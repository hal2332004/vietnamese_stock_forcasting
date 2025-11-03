import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { 
  Brain, 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Calendar,
  Sparkles,
  AlertCircle
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

const ModelInference = () => {
  const [selectedTimeframe, setSelectedTimeframe] = useState("");
  const [prediction, setPrediction] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handlePredict = () => {
    if (!selectedTimeframe) return;
    
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setPrediction({
        trend: "up", // "up" | "down" | "neutral"
        confidence: 85,
        predictedChange: 2.5,
        targetDate: "2025-11-10",
      });
      setIsLoading(false);
    }, 1500);
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
              Select timeframe for market prediction analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-3">
              <Label htmlFor="timeframe" className="text-base font-medium">
                Prediction Timeframe
              </Label>
              <Select value={selectedTimeframe} onValueChange={setSelectedTimeframe}>
                <SelectTrigger id="timeframe" className="w-full h-12">
                  <SelectValue placeholder="Select prediction timeframe..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1day">Next 1 Day</SelectItem>
                  <SelectItem value="3days">Next 3 Days</SelectItem>
                  <SelectItem value="1week">Next 1 Week</SelectItem>
                  <SelectItem value="2weeks">Next 2 Weeks</SelectItem>
                  <SelectItem value="1month">Next 1 Month</SelectItem>
                  <SelectItem value="3months">Next 3 Months</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-sm text-muted-foreground">
                Choose the time period for market trend prediction
              </p>
            </div>

            <Button 
              onClick={handlePredict}
              disabled={!selectedTimeframe || isLoading}
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
                Predictions are based on historical data and AI models. Use as reference only.
              </AlertDescription>
            </Alert>
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
                      {prediction.trend === "up" ? (
                        <div className="w-20 h-20 mx-auto rounded-full bg-green-500/10 flex items-center justify-center">
                          <TrendingUp className="w-10 h-10 text-green-500" />
                        </div>
                      ) : prediction.trend === "down" ? (
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
                      {prediction.trend === "up" ? "Bullish Trend" : 
                       prediction.trend === "down" ? "Bearish Trend" : "Neutral"}
                    </h3>
                    <Badge variant={prediction.trend === "up" ? "default" : "destructive"} className="text-sm">
                      {prediction.confidence}% Confidence
                    </Badge>
                  </div>
                </div>

                {/* Prediction Details */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 border rounded-lg bg-card">
                    <p className="text-sm text-muted-foreground mb-1">Predicted Change</p>
                    <p className={`text-2xl font-bold ${
                      prediction.predictedChange > 0 ? "text-green-500" : "text-red-500"
                    }`}>
                      {prediction.predictedChange > 0 ? "+" : ""}
                      {prediction.predictedChange}%
                    </p>
                  </div>
                  <div className="p-4 border rounded-lg bg-card">
                    <p className="text-sm text-muted-foreground mb-1">Target Date</p>
                    <p className="text-lg font-semibold text-foreground">
                      {new Date(prediction.targetDate).toLocaleDateString('vi-VN', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric'
                      })}
                    </p>
                  </div>
                </div>

                {/* Model Info */}
                <div className="p-4 bg-muted/30 rounded-lg border">
                  <p className="text-sm font-medium mb-2">Model Information</p>
                  <div className="space-y-1 text-sm text-muted-foreground">
                    <p>• Algorithm: LSTM Neural Network</p>
                    <p>• Training Data: 5 years historical</p>
                    <p>• Last Updated: Nov 3, 2025</p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Additional Info */}
      <Card className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20 border-2">
        <CardHeader>
          <CardTitle className="text-lg">How It Works</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            • <strong>AI Models:</strong> Uses advanced LSTM and Transformer models trained on Vietnamese stock market data
          </p>
          <p>
            • <strong>Data Sources:</strong> Analyzes historical prices, trading volumes, news sentiment, and technical indicators
          </p>
          <p>
            • <strong>Accuracy:</strong> Models are continuously retrained and validated against recent market movements
          </p>
          <p>
            • <strong>Disclaimer:</strong> Predictions are for reference only and should not be used as sole basis for investment decisions
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ModelInference;
