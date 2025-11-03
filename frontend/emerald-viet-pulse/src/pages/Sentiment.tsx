import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

export default function Sentiment() {
  const [sentimentData, setSentimentData] = useState<any[]>([]);
  const [dateRange, setDateRange] = useState({ start: new Date(2015, 0, 1), end: new Date() });

  useEffect(() => {
    loadSentimentData();
  }, [dateRange]);

  useEffect(() => {
    const handleTimeFilterChange = (event: any) => {
      const { start, end } = event.detail;
      setDateRange({ start, end });
    };

    window.addEventListener("timeFilterChange", handleTimeFilterChange);
    return () => window.removeEventListener("timeFilterChange", handleTimeFilterChange);
  }, []);

  const loadSentimentData = async () => {
    const startYear = dateRange.start.getFullYear();
    const endYear = dateRange.end.getFullYear();

    const { data } = await supabase
      .from("news_data")
      .select("ticker, positive_score, negative_score, neutral_score")
      .gte("year", startYear)
      .lte("year", endYear);

    if (data) {
      // Aggregate by ticker
      const aggregated = data.reduce((acc: any, item) => {
        if (!acc[item.ticker]) {
          acc[item.ticker] = {
            ticker: item.ticker,
            positive: 0,
            negative: 0,
            neutral: 0,
            count: 0,
          };
        }
        acc[item.ticker].positive += item.positive_score || 0;
        acc[item.ticker].negative += item.negative_score || 0;
        acc[item.ticker].neutral += item.neutral_score || 0;
        acc[item.ticker].count += 1;
        return acc;
      }, {});

      const result = Object.values(aggregated).map((item: any) => ({
        ticker: item.ticker,
        positive: (item.positive / item.count).toFixed(1),
        negative: (item.negative / item.count).toFixed(1),
        neutral: (item.neutral / item.count).toFixed(1),
      }));

      setSentimentData(result.slice(0, 15));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Sentiment Analytics</h1>
        <p className="text-muted-foreground">Track market sentiment across stocks</p>
      </div>

      <Card className="p-6 bg-card/60 backdrop-blur-sm border-border">
        <h3 className="text-lg font-semibold mb-4">Average Sentiment by Ticker</h3>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={sentimentData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis 
              dataKey="ticker" 
              stroke="hsl(var(--muted-foreground))"
              style={{ fontSize: "12px" }}
            />
            <YAxis 
              stroke="hsl(var(--muted-foreground))"
              style={{ fontSize: "12px" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
              }}
            />
            <Legend />
            <Bar dataKey="positive" fill="hsl(var(--positive))" name="Positive" />
            <Bar dataKey="negative" fill="hsl(var(--negative))" name="Negative" />
            <Bar dataKey="neutral" fill="hsl(var(--neutral))" name="Neutral" />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
