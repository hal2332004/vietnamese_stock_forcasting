import { Badge } from "@/components/ui/badge";

interface SentimentBadgeProps {
  positive: number;
  negative: number;
  neutral: number;
}

export const SentimentBadge = ({ positive, negative, neutral }: SentimentBadgeProps) => {
  const getSentiment = () => {
    const max = Math.max(positive, negative, neutral);
    if (max === positive) return { label: "Positive", color: "bg-positive text-primary-foreground" };
    if (max === negative) return { label: "Negative", color: "bg-negative text-foreground" };
    return { label: "Neutral", color: "bg-neutral text-foreground" };
  };

  const sentiment = getSentiment();

  return (
    <Badge className={`${sentiment.color} border-0`}>
      {sentiment.label}
    </Badge>
  );
};
