import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { 
  Brain, 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Calendar,
  Sparkles,
  AlertCircle,
  Database,
  Zap
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useToast } from "@/hooks/use-toast";

const API_BASE_URL = "http://localhost:8000";

interface DateRange {
  min_date: string;
  max_date: string;
  total_days: number;
}

interface ModelResult {
  prediction: number;
  actual: number;
  time_steps: number;
  error: number;
  error_pct: number;
}

interface PredictionSummary {
  trend: string;
  confidence: number;
  predicted_change: number;
  actual_change: number;
  models_used: string[];
}

interface PredictionResponse {
  target_date: string;
  predictions: Record<string, ModelResult>;
  summary: PredictionSummary;
}

const ModelInference = () => {
  const [selectedDate, setSelectedDate] = useState("");
  const [dateRange, setDateRange] = useState<DateRange | null>(null);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingRange, setIsLoadingRange] = useState(true);
  const { toast } = useToast();

  // Fetch date range on component mount
  useEffect(() => {
    fetchDateRange();
  }, []);

  const fetchDateRange = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/date-range`);
      if (!response.ok) {
        throw new Error("Failed to fetch date range");
      }
      const data = await response.json();
      setDateRange(data);
      // Set default date to max_date
      setSelectedDate(data.max_date);
    } catch (error) {
      toast({
        title: "Connection Error",
        description: "Cannot connect to prediction API. Please ensure the server is running.",
        variant: "destructive",
      });
    } finally {
      setIsLoadingRange(false);
    }
  };

  const handlePredict = async () => {
    if (!selectedDate) return;
    
    setIsLoading(true);
    setPrediction(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/predict`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ date: selectedDate }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Prediction failed");
      }
      
      const data: PredictionResponse = await response.json();
      setPrediction(data);
      
      toast({
        title: "Prediction Complete",
        description: `Successfully predicted for ${selectedDate}`,
      });
      
    } catch (error) {
      toast({
        title: "Prediction Error",
        description: error instanceof Error ? error.message : "Failed to make prediction",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
          <Brain className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-foreground">Model Inference</h1>
          <p className="text-muted-foreground">
            AI-powered market prediction and analysis
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section */}
        <Card className="border-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-primary" />
              Prediction Configuration
            </CardTitle>
            <CardDescription>
              Select a specific date for next-day price range prediction
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {isLoadingRange ? (
              <div className="flex items-center justify-center py-8">
                <Activity className="w-8 h-8 animate-spin text-primary" />
              </div>
            ) : dateRange ? (
              <>
                <div className="space-y-3">
                  <Label htmlFor="date" className="text-base font-medium">
                    Target Date
                  </Label>
                  <Input
                    id="date"
                    type="date"
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    min={dateRange.min_date}
                    max={dateRange.max_date}
                    className="w-full h-12 text-base"
                  />
                  <p className="text-sm text-muted-foreground">
                    Available range: {new Date(dateRange.min_date).toLocaleDateString('vi-VN')} - {new Date(dateRange.max_date).toLocaleDateString('vi-VN')}
                  </p>
                  <div className="flex items-center gap-2 text-sm">
                    <Database className="w-4 h-4 text-primary" />
                    <span className="text-muted-foreground">
                      {dateRange.total_days} days of data available
                    </span>
                  </div>
                </div>

                <Button 
                  onClick={handlePredict}
                  disabled={!selectedDate || isLoading}
                  className="w-full h-12 text-base gap-2"
                  size="lg"
                >
                  {isLoading ? (
                    <>
                      <Activity className="w-5 h-5 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      Run Prediction
                    </>
                  )}
                </Button>

                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-sm">
                    AI models predict the next day's price range (High-Low %) based on historical patterns and sentiment analysis.
                  </AlertDescription>
                </Alert>
              </>
            ) : (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Cannot connect to API server. Please ensure it's running on port 8000.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Results Section */}
        <Card className="border-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              Prediction Results
            </CardTitle>
            <CardDescription>
              AI-generated market trend forecast
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!prediction && !isLoading ? (
              <div className="flex flex-col items-center justify-center h-[300px] border-2 border-dashed border-border rounded-lg">
                <Brain className="w-16 h-16 text-muted-foreground mb-4" />
                <p className="text-muted-foreground text-center">
                  Select a timeframe and run prediction<br />to see results
                </p>
              </div>
            ) : isLoading ? (
              <div className="flex flex-col items-center justify-center h-[300px] border-2 border-dashed border-border rounded-lg bg-muted/20">
                <Activity className="w-16 h-16 text-primary animate-spin mb-4" />
                <p className="text-foreground font-medium">Analyzing market data...</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Running AI models on historical patterns
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Trend Indicator */}
                <div className="flex items-center justify-center p-6 bg-gradient-to-br from-background to-muted rounded-lg border-2">
                  <div className="text-center">
                    <div className="mb-3">
                      {prediction.summary.trend === "up" ? (
                        <div className="w-20 h-20 mx-auto rounded-full bg-green-500/10 flex items-center justify-center">
                          <TrendingUp className="w-10 h-10 text-green-500" />
                        </div>
                      ) : prediction.summary.trend === "down" ? (
                        <div className="w-20 h-20 mx-auto rounded-full bg-red-500/10 flex items-center justify-center">
                          <TrendingDown className="w-10 h-10 text-red-500" />
                        </div>
                      ) : (
                        <div className="w-20 h-20 mx-auto rounded-full bg-yellow-500/10 flex items-center justify-center">
                          <Activity className="w-10 h-10 text-yellow-500" />
                        </div>
                      )}
                    </div>
                    <h3 className="text-2xl font-bold mb-2">
                      {prediction.summary.trend === "up" ? "Bullish Trend" : 
                       prediction.summary.trend === "down" ? "Bearish Trend" : "Neutral"}
                    </h3>
                    <Badge variant={prediction.summary.trend === "up" ? "default" : "destructive"} className="text-sm">
                      {prediction.summary.confidence.toFixed(1)}% Confidence
                    </Badge>
                  </div>
                </div>

                {/* Prediction Details */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 border rounded-lg bg-card">
                    <p className="text-sm text-muted-foreground mb-1">Predicted Range</p>
                    <p className={`text-2xl font-bold ${
                      prediction.summary.predicted_change > 0 ? "text-green-500" : "text-red-500"
                    }`}>
                      {prediction.summary.predicted_change > 0 ? "+" : ""}
                      {prediction.summary.predicted_change.toFixed(4)}%
                    </p>
                  </div>
                  <div className="p-4 border rounded-lg bg-card">
                    <p className="text-sm text-muted-foreground mb-1">Actual Range</p>
                    <p className={`text-2xl font-bold ${
                      prediction.summary.actual_change > 0 ? "text-green-500" : "text-red-500"
                    }`}>
                      {prediction.summary.actual_change > 0 ? "+" : ""}
                      {prediction.summary.actual_change.toFixed(4)}%
                    </p>
                  </div>
                </div>

                {/* Target Date */}
                <div className="p-4 border rounded-lg bg-gradient-to-r from-primary/5 to-primary/10">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">Prediction Date</p>
                      <p className="text-xl font-semibold text-foreground">
                        {new Date(prediction.target_date).toLocaleDateString('vi-VN', {
                          weekday: 'long',
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric'
                        })}
                      </p>
                    </div>
                    <Calendar className="w-8 h-8 text-primary/50" />
                  </div>
                </div>

                {/* Model Results */}
                <div className="p-4 bg-muted/30 rounded-lg border space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="w-4 h-4 text-primary" />
                    <p className="text-sm font-medium">Model Details</p>
                  </div>
                  {Object.entries(prediction.predictions).map(([modelName, result]) => (
                    <div key={modelName} className="flex items-center justify-between text-sm p-2 bg-background rounded">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{modelName}</Badge>
                        <span className="text-muted-foreground text-xs">
                          {result.time_steps} days lookback
                        </span>
                      </div>
                      <div className="text-right">
                        <p className={`font-medium ${
                          result.prediction > 0 ? "text-green-600" : "text-red-600"
                        }`}>
                          {result.prediction > 0 ? "+" : ""}{result.prediction.toFixed(4)}%
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Error: {Math.abs(result.error_pct).toFixed(2)}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Additional Info */}
      <Card className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20 border-2">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Brain className="w-5 h-5" />
            How It Works
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            • <strong>AI Models:</strong> LSTM (30-day lookback) and Transformer (20-day lookback) neural networks trained on FPT stock data
          </p>
          <p>
            • <strong>Prediction Target:</strong> Next day's price range percentage (High - Low) / Close
          </p>
          <p>
            • <strong>Data Sources:</strong> Historical OHLCV, technical indicators (MA, RSI, MACD, Bollinger Bands), and news sentiment scores
          </p>
          <p>
            • <strong>Features:</strong> 33 engineered features including price lags, volatility measures, volume ratios, and sentiment metrics
          </p>
          <p>
            • <strong>Disclaimer:</strong> Predictions are for educational and reference purposes only. Not financial advice.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ModelInference;
