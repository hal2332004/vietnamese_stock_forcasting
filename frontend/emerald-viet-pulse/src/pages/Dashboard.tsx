import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { MetricCard } from "@/components/MetricCard";
import { StockChart } from "@/components/StockChart";
import { NewsCard } from "@/components/NewsCard";
import { TrendingUp, TrendingDown, Newspaper, BarChart3 } from "lucide-react";

export default function Dashboard() {
  const [metrics, setMetrics] = useState({
    positiveNews: 0,
    negativeNews: 0,
    neutralNews: 0,
    totalStocks: 0,
  });
  const [chartData, setChartData] = useState<Array<{ time: string; close: number }>>([]);
  const [recentNews, setRecentNews] = useState<any[]>([]);

  const [dateRange, setDateRange] = useState({ start: new Date(2015, 0, 1), end: new Date() });

  useEffect(() => {
    loadDashboardData();
  }, [dateRange]);

  useEffect(() => {
    const handleTimeFilterChange = (event: any) => {
      const { start, end } = event.detail;
      setDateRange({ start, end });
    };

    window.addEventListener("timeFilterChange", handleTimeFilterChange);
    return () => window.removeEventListener("timeFilterChange", handleTimeFilterChange);
  }, []);

  const loadDashboardData = async () => {
    // Load metrics
    const { data: newsData } = await supabase
      .from("news_data")
      .select("positive_score, negative_score, neutral_score");

    if (newsData) {
      const positive = newsData.filter((n) => (n.positive_score || 0) > (n.negative_score || 0) && (n.positive_score || 0) > (n.neutral_score || 0)).length;
      const negative = newsData.filter((n) => (n.negative_score || 0) > (n.positive_score || 0) && (n.negative_score || 0) > (n.neutral_score || 0)).length;
      const neutral = newsData.filter((n) => (n.neutral_score || 0) >= (n.positive_score || 0) && (n.neutral_score || 0) >= (n.negative_score || 0)).length;

      setMetrics({
        positiveNews: positive,
        negativeNews: negative,
        neutralNews: neutral,
        totalStocks: 0,
      });
    }

    // Load chart data (sample stock)
    const { data: stockData } = await supabase
      .from("stock_data")
      .select("time, close")
      .order("time", { ascending: true })
      .limit(30);

    if (stockData) {
      setChartData(
        stockData.map((item) => ({
          time: new Date(item.time).toLocaleDateString("vi-VN"),
          close: item.close || 0,
        }))
      );
    }

    // Load recent news
    const { data: news } = await supabase
      .from("news_data")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(5);

    if (news) {
      setRecentNews(news);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-primary to-foreground bg-clip-text text-transparent">
          Market Overview
        </h1>
        <p className="text-muted-foreground">Vietnamese Stock Market Analytics</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Positive News"
          value={metrics.positiveNews}
          icon={TrendingUp}
          color="positive"
        />
        <MetricCard
          title="Negative News"
          value={metrics.negativeNews}
          icon={TrendingDown}
          color="negative"
        />
        <MetricCard
          title="Neutral News"
          value={metrics.neutralNews}
          icon={Newspaper}
          color="neutral"
        />
        <MetricCard
          title="Total Stocks"
          value={metrics.totalStocks}
          icon={BarChart3}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StockChart data={chartData} title="Market Trend (Last 30 Days)" />
        
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Recent News</h3>
          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
            {recentNews.map((news) => (
              <NewsCard
                key={news.id}
                title={news.title}
                date={news.date || ""}
                source={news.source || "Unknown"}
                ticker={news.ticker}
                positiveScore={news.positive_score || 0}
                negativeScore={news.negative_score || 0}
                neutralScore={news.neutral_score || 0}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
