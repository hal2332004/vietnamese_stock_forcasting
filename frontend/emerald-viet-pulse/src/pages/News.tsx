import { useState, useEffect } from "react";
import { supabase } from "@/integrations/supabase/client";
import { NewsCard } from "@/components/NewsCard";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";

export default function News() {
  const [news, setNews] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [dateRange, setDateRange] = useState({ start: new Date(2015, 0, 1), end: new Date() });

  useEffect(() => {
    loadNews();
  }, [dateRange]);

  useEffect(() => {
    const handleTimeFilterChange = (event: any) => {
      const { start, end } = event.detail;
      setDateRange({ start, end });
    };

    window.addEventListener("timeFilterChange", handleTimeFilterChange);
    return () => window.removeEventListener("timeFilterChange", handleTimeFilterChange);
  }, []);

  const loadNews = async () => {
    const startYear = dateRange.start.getFullYear();
    const endYear = dateRange.end.getFullYear();

    const { data } = await supabase
      .from("news_data")
      .select("*")
      .gte("year", startYear)
      .lte("year", endYear)
      .order("created_at", { ascending: false })
      .limit(100);

    if (data) {
      setNews(data);
    }
  };

  const filteredNews = news.filter((item) =>
    item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.ticker.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">News Analysis</h1>
        <p className="text-muted-foreground">Latest market news with sentiment analysis</p>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search by title or ticker..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10 bg-card border-border"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filteredNews.map((item) => (
          <NewsCard
            key={item.id}
            title={item.title}
            date={item.date || ""}
            source={item.source || "Unknown"}
            ticker={item.ticker}
            positiveScore={item.positive_score || 0}
            negativeScore={item.negative_score || 0}
            neutralScore={item.neutral_score || 0}
            content={item.content}
          />
        ))}
      </div>
    </div>
  );
}
