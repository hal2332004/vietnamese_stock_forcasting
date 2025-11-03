import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Calendar } from "lucide-react";

export type TimeFilterOption = "1D" | "1W" | "1M" | "3M" | "6M" | "1Y" | "YTD" | "ALL" | "CUSTOM";

const filterOptions: TimeFilterOption[] = ["1D", "1W", "1M", "3M", "6M", "1Y", "YTD", "ALL"];

export const getDateRange = (filter: TimeFilterOption): { start: Date; end: Date } => {
  const end = new Date();
  const start = new Date();

  switch (filter) {
    case "1D":
      start.setDate(end.getDate() - 1);
      break;
    case "1W":
      start.setDate(end.getDate() - 7);
      break;
    case "1M":
      start.setMonth(end.getMonth() - 1);
      break;
    case "3M":
      start.setMonth(end.getMonth() - 3);
      break;
    case "6M":
      start.setMonth(end.getMonth() - 6);
      break;
    case "1Y":
      start.setFullYear(end.getFullYear() - 1);
      break;
    case "YTD":
      start.setMonth(0, 1);
      break;
    case "ALL":
      start.setFullYear(2015, 0, 1);
      break;
    default:
      start.setMonth(end.getMonth() - 1);
  }

  return { start, end };
};

export const TimeFilter = () => {
  const [activeFilter, setActiveFilter] = useState<TimeFilterOption>(() => {
    const saved = localStorage.getItem("timeFilter");
    return (saved as TimeFilterOption) || "ALL";
  });

  useEffect(() => {
    localStorage.setItem("timeFilter", activeFilter);
    const dateRange = getDateRange(activeFilter);
    window.dispatchEvent(new CustomEvent("timeFilterChange", { 
      detail: { filter: activeFilter, ...dateRange } 
    }));
  }, [activeFilter]);

  return (
    <div className="sticky top-16 z-30 bg-card/80 backdrop-blur-md border-b border-border px-4 py-3">
      <div className="flex items-center gap-2 overflow-x-auto">
        {filterOptions.map((option) => (
          <Button
            key={option}
            onClick={() => setActiveFilter(option)}
            variant={activeFilter === option ? "default" : "outline"}
            size="sm"
            className={
              activeFilter === option
                ? "bg-primary text-primary-foreground hover:bg-primary-hover"
                : "border-primary text-foreground hover:bg-primary/10"
            }
          >
            {option}
          </Button>
        ))}
        <Button
          onClick={() => setActiveFilter("CUSTOM")}
          variant={activeFilter === "CUSTOM" ? "default" : "outline"}
          size="sm"
          className={
            activeFilter === "CUSTOM"
              ? "bg-primary text-primary-foreground hover:bg-primary-hover"
              : "border-primary text-foreground hover:bg-primary/10"
          }
        >
          <Calendar className="w-4 h-4 mr-1" />
          Custom
        </Button>
      </div>
    </div>
  );
};
