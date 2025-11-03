import { ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  color?: "positive" | "negative" | "neutral";
}

export const MetricCard = ({ title, value, icon: Icon, trend, color = "neutral" }: MetricCardProps) => {
  const colorClasses = {
    positive: "text-positive",
    negative: "text-negative",
    neutral: "text-neutral",
  };

  return (
    <Card className="p-6 bg-card/60 backdrop-blur-sm border-border hover:shadow-[0_0_40px_hsl(var(--primary)/0.15)] transition-all">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted-foreground mb-1">{title}</p>
          <h3 className={`text-3xl font-bold ${colorClasses[color]}`}>{value}</h3>
          {trend && (
            <p className={`text-sm mt-2 ${trend.isPositive ? "text-positive" : "text-negative"}`}>
              {trend.isPositive ? "↑" : "↓"} {Math.abs(trend.value)}%
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg bg-${color}/10`}>
          <Icon className={`w-6 h-6 ${colorClasses[color]}`} />
        </div>
      </div>
    </Card>
  );
};
