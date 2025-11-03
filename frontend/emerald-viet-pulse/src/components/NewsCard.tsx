import { Card } from "@/components/ui/card";
import { SentimentBadge } from "./SentimentBadge";
import { Clock } from "lucide-react";

interface NewsCardProps {
  title: string;
  date: string;
  source: string;
  ticker: string;
  positiveScore: number;
  negativeScore: number;
  neutralScore: number;
  content?: string;
}

export const NewsCard = ({
  title,
  date,
  source,
  ticker,
  positiveScore,
  negativeScore,
  neutralScore,
  content,
}: NewsCardProps) => {
  return (
    <Card className="p-5 bg-card/60 backdrop-blur-sm border-border hover:border-primary/50 transition-all group">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1">
          <h4 className="font-semibold text-foreground mb-2 group-hover:text-primary transition-colors">
            {title}
          </h4>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {date}
            </span>
            <span>•</span>
            <span>{source}</span>
            <span>•</span>
            <span className="font-mono text-primary">{ticker}</span>
          </div>
        </div>
        <SentimentBadge
          positive={positiveScore}
          negative={negativeScore}
          neutral={neutralScore}
        />
      </div>
      
      {content && (
        <p className="text-sm text-muted-foreground line-clamp-2 mb-3">{content}</p>
      )}

      <div className="flex-1 h-1.5 rounded-full bg-secondary overflow-hidden">
        <div className="flex h-full">
          <div
            className="bg-positive"
            style={{ width: `${positiveScore}%` }}
          />
          <div
            className="bg-negative"
            style={{ width: `${negativeScore}%` }}
          />
          <div
            className="bg-neutral"
            style={{ width: `${neutralScore}%` }}
          />
        </div>
      </div>
    </Card>
  );
};
