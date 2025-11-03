import { useState, useEffect } from "react";
import { supabase } from "@/integrations/supabase/client";
import { StockChart } from "@/components/StockChart";
import { StockDataTable } from "@/components/StockDataTable";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const TARGET_TICKERS = ["ACB", "BID", "FPT", "MBB", "VCB"];

export default function Stocks() {
  const [selectedTicker, setSelectedTicker] = useState<string>("ACB");
  const [stockData, setStockData] = useState<any[]>([]);
  const [allStocksData, setAllStocksData] = useState<any[]>([]);
  const [dateRange, setDateRange] = useState({ start: new Date(2015, 0, 1), end: new Date() });

  useEffect(() => {
    loadStockData(selectedTicker);
    loadAllStocksData();
  }, [selectedTicker, dateRange]);

  useEffect(() => {
    const handleTimeFilterChange = (event: any) => {
      const { start, end } = event.detail;
      setDateRange({ start, end });
    };

    window.addEventListener("timeFilterChange", handleTimeFilterChange);
    return () => window.removeEventListener("timeFilterChange", handleTimeFilterChange);
  }, []);

  const loadStockData = async (ticker: string) => {
    const { data } = await supabase
      .from("stock_data")
      .select("*")
      .eq("ticker", ticker)
      .gte("time", dateRange.start.toISOString().split("T")[0])
      .lte("time", dateRange.end.toISOString().split("T")[0])
      .order("time", { ascending: true });

    if (data) {
      setStockData(data);
    }
  };

  const loadAllStocksData = async () => {
    const { data } = await supabase
      .from("stock_data")
      .select("*")
      .in("ticker", TARGET_TICKERS)
      .gte("time", dateRange.start.toISOString().split("T")[0])
      .lte("time", dateRange.end.toISOString().split("T")[0])
      .order("time", { ascending: false })
      .limit(500);

    if (data) {
      setAllStocksData(data);
    }
  };

  const chartData = stockData.map((item) => ({
    time: new Date(item.time).toLocaleDateString("vi-VN"),
    close: item.close || 0,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Dữ liệu Cổ phiếu</h1>
          <p className="text-muted-foreground">Phân tích chi tiết 5 mã cổ phiếu (2015-2025)</p>
        </div>
        <Select value={selectedTicker} onValueChange={setSelectedTicker}>
          <SelectTrigger className="w-[180px] bg-card border-border">
            <SelectValue placeholder="Chọn mã CP" />
          </SelectTrigger>
          <SelectContent>
            {TARGET_TICKERS.map((ticker) => (
              <SelectItem key={ticker} value={ticker}>
                {ticker}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Tabs defaultValue="all" className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="all">Tất cả cổ phiếu</TabsTrigger>
          <TabsTrigger value="detail">Chi tiết {selectedTicker}</TabsTrigger>
        </TabsList>
        
        <TabsContent value="all" className="space-y-6 mt-6">
          <StockDataTable 
            data={allStocksData.map(item => ({
              ticker: item.ticker,
              time: item.time,
              open: item.open || 0,
              high: item.high || 0,
              low: item.low || 0,
              close: item.close || 0,
              volume: item.volume || 0,
            }))}
          />
        </TabsContent>

        <TabsContent value="detail" className="space-y-6 mt-6">
          {stockData.length > 0 && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="p-4 bg-card/60 backdrop-blur-sm border-border">
                  <p className="text-sm text-muted-foreground mb-1">Mở cửa</p>
                  <p className="text-xl font-bold text-foreground">
                    {stockData[stockData.length - 1]?.open?.toFixed(2)}
                  </p>
                </Card>
                <Card className="p-4 bg-card/60 backdrop-blur-sm border-border">
                  <p className="text-sm text-muted-foreground mb-1">Cao nhất</p>
                  <p className="text-xl font-bold text-positive">
                    {stockData[stockData.length - 1]?.high?.toFixed(2)}
                  </p>
                </Card>
                <Card className="p-4 bg-card/60 backdrop-blur-sm border-border">
                  <p className="text-sm text-muted-foreground mb-1">Thấp nhất</p>
                  <p className="text-xl font-bold text-negative">
                    {stockData[stockData.length - 1]?.low?.toFixed(2)}
                  </p>
                </Card>
                <Card className="p-4 bg-card/60 backdrop-blur-sm border-border">
                  <p className="text-sm text-muted-foreground mb-1">Khối lượng</p>
                  <p className="text-xl font-bold text-foreground">
                    {(stockData[stockData.length - 1]?.volume || 0).toLocaleString()}
                  </p>
                </Card>
              </div>

              <StockChart data={chartData} title={`Biểu đồ giá ${selectedTicker}`} />
              
              <StockDataTable 
                data={stockData.slice(-100).map(item => ({
                  ticker: item.ticker,
                  time: item.time,
                  open: item.open || 0,
                  high: item.high || 0,
                  low: item.low || 0,
                  close: item.close || 0,
                  volume: item.volume || 0,
                }))}
              />
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
