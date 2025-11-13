import { useState, useEffect } from "react";import { useState, useEffect } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { Button } from "@/components/ui/button";import { Button } from "@/components/ui/button";

import { Label } from "@/components/ui/label";import { Label } from "@/components/ui/label";

import {import {

  Select,  Select,

  SelectContent,  SelectContent,

  SelectItem,  SelectItem,

  SelectTrigger,  SelectTrigger,

  SelectValue,  SelectValue,

} from "@/components/ui/select";} from "@/components/ui/select";

import { Badge } from "@/components/ui/badge";import { Badge } from "@/components/ui/badge";

import { import { 

  Brain, TrendingUp, TrendingDown, Activity, Calendar,  Brain, 

  Sparkles, AlertCircle, RefreshCw, Target, BarChart3,  TrendingUp, 

  AlertTriangle, CheckCircle2, Info  TrendingDown, 

} from "lucide-react";  Activity, 

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";  Calendar,

import { toast } from "sonner";  Sparkles,

  AlertCircle,

// Updated API Configuration - Using unified backend on port 8001  RefreshCw

const API_BASE_URL = "http://localhost:8001";} from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";

// Type Definitionsimport { toast } from "sonner";

interface DirectionPrediction {

  prediction: number;// API Configuration

  label: string;const API_BASE_URL = "http://localhost:8000";

  probability: number;

  threshold: number;interface PredictionResult {

  confidence: number;  prediction: number;

  model: string;  actual: number;

}  time_steps: number;

  error: number;

interface VolatilityPrediction {  error_pct: number;

  predicted_range_pct: number;}

  confidence: number;

  model: string;interface ApiResponse {

}  target_date: string;

  predictions: {

interface PriceForecast {    LSTM?: PredictionResult;

  direction: string;    Transformer?: PredictionResult;

  expected_range: string;  };

  estimated_high: number;  summary: {

  estimated_low: number;    trend: string;

}    confidence: number;

    predicted_change: number;

interface ActualResults {    actual_change: number;

  price: number | null;    models_used: string[];

  high: number | null;  };

  low: number | null;}

  return_pct: number | null;

  direction: number | null;const ModelInference = () => {

  label: string | null;  const [selectedDate, setSelectedDate] = useState("");

  range_pct: number | null;  const [availableDates, setAvailableDates] = useState<string[]>([]);

}  const [dateRange, setDateRange] = useState<any>(null);

  const [prediction, setPrediction] = useState<ApiResponse | null>(null);

interface AccuracyMetrics {  const [isLoading, setIsLoading] = useState(false);

  direction_correct: boolean | null;  const [isLoadingDates, setIsLoadingDates] = useState(true);

  range_error_pct: number | null;

}  // Fetch available dates on mount

  useEffect(() => {

interface TradingRecommendation {    fetchDateRange();

  signal: string;    fetchAvailableDates();

  confidence_pct: number;  }, []);

  action: string;

  risk_level: string;  const fetchDateRange = async () => {

  stop_loss_suggestion: string | null;    try {

}      const response = await fetch(`${API_BASE_URL}/date-range`);

      if (!response.ok) throw new Error("Failed to fetch date range");

interface LSTMPredictionResponse {      const data = await response.json();

  ticker: string;      setDateRange(data);

  target_date: string;    } catch (error) {

  current_price: number;      console.error("Error fetching date range:", error);

  direction: DirectionPrediction;      toast.error("Failed to load date range");

  volatility: VolatilityPrediction;    }

  price_forecast: PriceForecast;  };

  actual: ActualResults;

  accuracy: AccuracyMetrics;  const fetchAvailableDates = async () => {

  recommendation: TradingRecommendation;    setIsLoadingDates(true);

  timestamp: string;    try {

}      const response = await fetch(`${API_BASE_URL}/available-dates?limit=60`);

      if (!response.ok) throw new Error("Failed to fetch dates");

const ModelInference = () => {      const data = await response.json();

  const [selectedTicker, setSelectedTicker] = useState("FPT");      setAvailableDates(data.dates);

  const [selectedDate, setSelectedDate] = useState("");    } catch (error) {

  const [availableDates, setAvailableDates] = useState<string[]>([]);      console.error("Error fetching available dates:", error);

  const [dateRange, setDateRange] = useState<any>(null);      toast.error("Failed to load available dates. Make sure API server is running.");

  const [prediction, setPrediction] = useState<LSTMPredictionResponse | null>(null);    } finally {

  const [isLoading, setIsLoading] = useState(false);      setIsLoadingDates(false);

  const [isLoadingDates, setIsLoadingDates] = useState(true);    }

  const [modelInfo, setModelInfo] = useState<any>(null);  };



  useEffect(() => {  const handlePredict = async () => {

    fetchDateRange();    if (!selectedDate) {

    fetchModelInfo();      toast.error("Please select a date");

  }, []);      return;

    }

  useEffect(() => {    

    if (selectedTicker) {    setIsLoading(true);

      fetchAvailableDates(selectedTicker);    setPrediction(null);

    }    

  }, [selectedTicker]);    try {

      const response = await fetch(`${API_BASE_URL}/predict`, {

  const fetchDateRange = async () => {        method: "POST",

    try {        headers: {

      const response = await fetch(`${API_BASE_URL}/api/lstm/date-range`);          "Content-Type": "application/json",

      if (!response.ok) throw new Error("Failed to fetch date range");        },

      const data = await response.json();        body: JSON.stringify({ date: selectedDate }),

      setDateRange(data);      });

    } catch (error) {

      console.error("Error fetching date range:", error);      if (!response.ok) {

      toast.error("Failed to load date range");        const errorData = await response.json();

    }        throw new Error(errorData.detail || "Prediction failed");

  };      }



  const fetchAvailableDates = async (ticker: string) => {      const data: ApiResponse = await response.json();

    setIsLoadingDates(true);      setPrediction(data);

    try {      toast.success("Prediction completed successfully!");

      const response = await fetch(`${API_BASE_URL}/api/lstm/available-dates?ticker=${ticker}&limit=60`);      

      if (!response.ok) throw new Error("Failed to fetch dates");    } catch (error: any) {

      const data = await response.json();      console.error("Error making prediction:", error);

      setAvailableDates(data.dates);      toast.error(error.message || "Failed to get prediction");

          } finally {

      if (data.note && data.note.includes("Error")) {      setIsLoading(false);

        toast.warning(data.note);    }

      }  };

    } catch (error) {

      console.error("Error fetching available dates:", error);  return (

      toast.error("Failed to load dates. Ensure API is running on port 8001.");    <div className="space-y-6">

    } finally {      {/* Header */}

      setIsLoadingDates(false);      <div className="flex items-center gap-3">

    }        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">

  };          <Brain className="w-6 h-6 text-white" />

        </div>

  const fetchModelInfo = async () => {        <div>

    try {          <h1 className="text-3xl font-bold text-foreground">Model Inference</h1>

      const response = await fetch(`${API_BASE_URL}/api/lstm/model-info`);          <p className="text-muted-foreground">

      if (!response.ok) throw new Error("Failed to fetch model info");            AI-powered market prediction and analysis

      const data = await response.json();          </p>

      setModelInfo(data);        </div>

    } catch (error) {      </div>

      console.error("Error fetching model info:", error);

    }      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

  };        {/* Input Section */}

        <Card className="border-2">

  const handlePredict = async () => {          <CardHeader>

    if (!selectedDate) {            <CardTitle className="flex items-center gap-2">

      toast.error("Please select a date");              <Calendar className="w-5 h-5 text-primary" />

      return;              Prediction Configuration

    }            </CardTitle>

                <CardDescription>

    setIsLoading(true);              Select timeframe for market prediction analysis

    setPrediction(null);            </CardDescription>

              </CardHeader>

    try {          <CardContent className="space-y-6">

      const response = await fetch(`${API_BASE_URL}/api/lstm/predict`, {            {/* Date Range Info */}

        method: "POST",            {dateRange && (

        headers: { "Content-Type": "application/json" },              <div className="p-3 bg-muted/30 rounded-lg border text-sm">

        body: JSON.stringify({ ticker: selectedTicker, date: selectedDate }),                <p className="font-medium mb-1">Available Data Range</p>

      });                <p className="text-muted-foreground">

                  From {new Date(dateRange.min_date).toLocaleDateString('vi-VN')} to{' '}

      if (!response.ok) {                  {new Date(dateRange.max_date).toLocaleDateString('vi-VN')}

        const errorData = await response.json();                </p>

        throw new Error(errorData.detail || "Prediction failed");                <p className="text-xs text-muted-foreground mt-1">

      }                  ({dateRange.total_days} days available)

                </p>

      const data: LSTMPredictionResponse = await response.json();              </div>

      setPrediction(data);            )}

      toast.success("Prediction completed successfully!");

                  <div className="space-y-3">

    } catch (error: any) {              <div className="flex items-center justify-between">

      console.error("Error making prediction:", error);                <Label htmlFor="date-select" className="text-base font-medium">

      toast.error(error.message || "Failed to get prediction");                  Select Prediction Date

    } finally {                </Label>

      setIsLoading(false);                <Button

    }                  variant="ghost"

  };                  size="sm"

                  onClick={fetchAvailableDates}

  const getSignalColor = (signal: string) => {                  disabled={isLoadingDates}

    if (signal.includes("STRONG BUY") || signal.includes("🟢"))                   className="h-8 gap-1"

      return "text-green-600 bg-green-50 border-green-200";                >

    if (signal.includes("STRONG SELL") || signal.includes("🔴"))                   <RefreshCw className={`w-3 h-3 ${isLoadingDates ? 'animate-spin' : ''}`} />

      return "text-red-600 bg-red-50 border-red-200";                  Refresh

    if (signal.includes("MODERATE"))                 </Button>

      return "text-yellow-600 bg-yellow-50 border-yellow-200";              </div>

    return "text-gray-600 bg-gray-50 border-gray-200";              

  };              <Select 

                value={selectedDate} 

  return (                onValueChange={setSelectedDate}

    <div className="space-y-6">                disabled={isLoadingDates}

      {/* Header */}              >

      <div className="flex items-center gap-3">                <SelectTrigger id="date-select" className="w-full h-12">

        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">                  <SelectValue placeholder={

          <Brain className="w-6 h-6 text-white" />                    isLoadingDates 

        </div>                      ? "Loading dates..." 

        <div>                      : availableDates.length > 0 

          <h1 className="text-3xl font-bold text-foreground">LSTM Model Inference</h1>                        ? "Select a date to predict..." 

          <p className="text-muted-foreground">                        : "No dates available"

            Dual-model prediction: Direction + Volatility with news sentiment                  } />

          </p>                </SelectTrigger>

        </div>                <SelectContent className="max-h-[300px]">

      </div>                  {availableDates.map((date) => (

                    <SelectItem key={date} value={date}>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">                      {new Date(date).toLocaleDateString('vi-VN', {

        {/* Input Section */}                        weekday: 'short',

        <Card className="border-2">                        year: 'numeric',

          <CardHeader>                        month: 'short',

            <CardTitle className="flex items-center gap-2">                        day: 'numeric'

              <Calendar className="w-5 h-5 text-primary" />                      })}

              Prediction Configuration                    </SelectItem>

            </CardTitle>                  ))}

            <CardDescription>                </SelectContent>

              Select stock and date for AI-powered market prediction              </Select>

            </CardDescription>              <p className="text-sm text-muted-foreground">

          </CardHeader>                Select a historical date to see next-day prediction vs actual

          <CardContent className="space-y-6">              </p>

            {dateRange && (            </div>

              <Alert>

                <Info className="h-4 w-4" />            <Button 

                <AlertTitle>Available Data Range</AlertTitle>              onClick={handlePredict}

                <AlertDescription>              disabled={!selectedDate || isLoading || isLoadingDates}

                  From {new Date(dateRange.min_date).toLocaleDateString('vi-VN')} to{' '}              className="w-full h-12 text-base gap-2"

                  {new Date(dateRange.max_date).toLocaleDateString('vi-VN')}              size="lg"

                  <br /><span className="text-xs">{dateRange.note}</span>            >

                </AlertDescription>              {isLoading ? (

              </Alert>                <>

            )}                  <Activity className="w-5 h-5 animate-spin" />

                  Analyzing with AI Models...

            {/* Stock Ticker */}                </>

            <div className="space-y-3">              ) : (

              <Label htmlFor="ticker-select" className="text-base font-medium">Stock Ticker</Label>                <>

              <Select value={selectedTicker} onValueChange={setSelectedTicker}>                  <Sparkles className="w-5 h-5" />

                <SelectTrigger id="ticker-select" className="w-full h-12">                  Run Prediction

                  <SelectValue placeholder="Select stock..." />                </>

                </SelectTrigger>              )}

                <SelectContent>            </Button>

                  {["ACB", "BID", "FPT", "MBB", "VCB"].map((ticker) => (

                    <SelectItem key={ticker} value={ticker}>            <Alert>

                      <div className="flex items-center gap-2">              <AlertCircle className="h-4 w-4" />

                        <span className="font-semibold">{ticker}</span>              <AlertDescription className="text-sm">

                        {modelInfo && (                <strong>Note:</strong> API server must be running on localhost:8000

                          <span className="text-xs text-muted-foreground">                <br />

                            Acc: {modelInfo.performance[ticker]?.accuracy || "N/A"}                Run: <code className="text-xs bg-muted px-1 py-0.5 rounded">python api_predict.py</code>

                          </span>              </AlertDescription>

                        )}            </Alert>

                      </div>          </CardContent>

                    </SelectItem>        </Card>

                  ))}

                </SelectContent>        {/* Results Section */}

              </Select>        <Card className="border-2">

            </div>          <CardHeader>

            <CardTitle className="flex items-center gap-2">

            {/* Date Selection */}              <Activity className="w-5 h-5 text-primary" />

            <div className="space-y-3">              Prediction Results

              <div className="flex items-center justify-between">            </CardTitle>

                <Label htmlFor="date-select" className="text-base font-medium">            <CardDescription>

                  Select Prediction Date              AI-generated market trend forecast

                </Label>            </CardDescription>

                <Button          </CardHeader>

                  variant="ghost" size="sm"          <CardContent>

                  onClick={() => fetchAvailableDates(selectedTicker)}            {!prediction && !isLoading ? (

                  disabled={isLoadingDates}              <div className="flex flex-col items-center justify-center h-[300px] border-2 border-dashed border-border rounded-lg">

                  className="h-8 gap-1"                <Brain className="w-16 h-16 text-muted-foreground mb-4" />

                >                <p className="text-muted-foreground text-center">

                  <RefreshCw className={`w-3 h-3 ${isLoadingDates ? 'animate-spin' : ''}`} />                  Select a date and run prediction<br />to see AI model results

                  Refresh                </p>

                </Button>              </div>

              </div>            ) : isLoading ? (

                            <div className="flex flex-col items-center justify-center h-[300px] border-2 border-dashed border-border rounded-lg bg-muted/20">

              <Select                 <Activity className="w-16 h-16 text-primary animate-spin mb-4" />

                value={selectedDate}                 <p className="text-foreground font-medium">Analyzing market data...</p>

                onValueChange={setSelectedDate}                <p className="text-sm text-muted-foreground mt-2">

                disabled={isLoadingDates}                  Running LSTM & Transformer models

              >                </p>

                <SelectTrigger id="date-select" className="w-full h-12">              </div>

                  <SelectValue placeholder={            ) : prediction ? (

                    isLoadingDates ? "Loading dates..." :               <div className="space-y-6">

                    availableDates.length > 0 ? "Select a date..." : "No dates available"                {/* Trend Indicator */}

                  } />                <div className="flex items-center justify-center p-6 bg-gradient-to-br from-background to-muted rounded-lg border-2">

                </SelectTrigger>                  <div className="text-center">

                <SelectContent className="max-h-[300px]">                    <div className="mb-3">

                  {availableDates.map((date) => (                      {prediction.summary.trend === "up" ? (

                    <SelectItem key={date} value={date}>                        <div className="w-20 h-20 mx-auto rounded-full bg-green-500/10 flex items-center justify-center">

                      {new Date(date).toLocaleDateString('vi-VN', {                          <TrendingUp className="w-10 h-10 text-green-500" />

                        weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'                        </div>

                      })}                      ) : prediction.summary.trend === "down" ? (

                    </SelectItem>                        <div className="w-20 h-20 mx-auto rounded-full bg-red-500/10 flex items-center justify-center">

                  ))}                          <TrendingDown className="w-10 h-10 text-red-500" />

                </SelectContent>                        </div>

              </Select>                      ) : (

              <p className="text-sm text-muted-foreground">                        <div className="w-20 h-20 mx-auto rounded-full bg-yellow-500/10 flex items-center justify-center">

                Model predicts next trading day from selected date                          <Activity className="w-10 h-10 text-yellow-500" />

              </p>                        </div>

            </div>                      )}

                    </div>

            <Button                     <h3 className="text-2xl font-bold mb-2">

              onClick={handlePredict}                      {prediction.summary.trend === "up" ? "Bullish Trend" : 

              disabled={!selectedDate || isLoading || isLoadingDates}                       prediction.summary.trend === "down" ? "Bearish Trend" : "Neutral"}

              className="w-full h-12 text-base gap-2" size="lg"                    </h3>

            >                    <Badge variant={prediction.summary.trend === "up" ? "default" : "destructive"} className="text-sm">

              {isLoading ? (                      {prediction.summary.confidence.toFixed(1)}% Confidence

                <>                    </Badge>

                  <Activity className="w-5 h-5 animate-spin" />                  </div>

                  Running Dual-Model Prediction...                </div>

                </>

              ) : (                {/* Prediction vs Actual */}

                <>                <div className="grid grid-cols-2 gap-4">

                  <Sparkles className="w-5 h-5" />                  <div className="p-4 border rounded-lg bg-card">

                  Run LSTM Prediction                    <p className="text-sm text-muted-foreground mb-1">Predicted Range</p>

                </>                    <p className={`text-2xl font-bold ${

              )}                      prediction.summary.predicted_change > 0 ? "text-green-500" : "text-red-500"

            </Button>                    }`}>

                      {prediction.summary.predicted_change > 0 ? "+" : ""}

            <Alert>                      {prediction.summary.predicted_change.toFixed(4)}%

              <AlertCircle className="h-4 w-4" />                    </p>

              <AlertDescription className="text-sm">                  </div>

                <strong>Models:</strong> Direction (Bi-LSTM 64→32, 44 features + news) + Volatility (Bi-LSTM 128→128, 38 indicators)                  <div className="p-4 border rounded-lg bg-card">

                <br /><strong>API:</strong> localhost:8001                    <p className="text-sm text-muted-foreground mb-1">Actual Range</p>

              </AlertDescription>                    <p className={`text-2xl font-bold ${

            </Alert>                      prediction.summary.actual_change > 0 ? "text-green-500" : "text-red-500"

          </CardContent>                    }`}>

        </Card>                      {prediction.summary.actual_change > 0 ? "+" : ""}

                      {prediction.summary.actual_change.toFixed(4)}%

        {/* Results Section */}                    </p>

        <Card className="border-2">                  </div>

          <CardHeader>                </div>

            <CardTitle className="flex items-center gap-2">

              <Target className="w-5 h-5 text-primary" />                {/* Model Predictions */}

              Prediction Results                <div className="space-y-3">

            </CardTitle>                  <p className="text-sm font-medium">Individual Model Results</p>

            <CardDescription>                  {prediction.predictions.LSTM && (

              Comprehensive market analysis and trading recommendations                    <div className="p-4 border rounded-lg bg-card">

            </CardDescription>                      <div className="flex items-center justify-between mb-2">

          </CardHeader>                        <span className="font-semibold text-blue-600">LSTM Model</span>

          <CardContent>                        <Badge variant="outline" className="text-xs">

            {!prediction && !isLoading ? (                          {prediction.predictions.LSTM.time_steps} days lookback

              <div className="flex flex-col items-center justify-center h-[500px] border-2 border-dashed border-border rounded-lg">                        </Badge>

                <Brain className="w-16 h-16 text-muted-foreground mb-4" />                      </div>

                <p className="text-muted-foreground text-center">                      <div className="grid grid-cols-3 gap-2 text-sm">

                  Select ticker and date, then run prediction<br />to see comprehensive AI analysis                        <div>

                </p>                          <p className="text-muted-foreground">Prediction</p>

              </div>                          <p className="font-semibold">{prediction.predictions.LSTM.prediction.toFixed(4)}%</p>

            ) : isLoading ? (                        </div>

              <div className="flex flex-col items-center justify-center h-[500px] border-2 border-dashed border-border rounded-lg bg-muted/20">                        <div>

                <Activity className="w-16 h-16 text-primary animate-spin mb-4" />                          <p className="text-muted-foreground">Error</p>

                <p className="text-foreground font-medium">Analyzing market data...</p>                          <p className="font-semibold">{prediction.predictions.LSTM.error.toFixed(4)}%</p>

                <p className="text-sm text-muted-foreground mt-2">                        </div>

                  Running dual LSTM models with news sentiment                        <div>

                </p>                          <p className="text-muted-foreground">Error %</p>

              </div>                          <p className="font-semibold">{prediction.predictions.LSTM.error_pct.toFixed(2)}%</p>

            ) : prediction ? (                        </div>

              <div className="space-y-4 max-h-[700px] overflow-y-auto pr-2">                      </div>

                {/* Trading Recommendation */}                    </div>

                <div className={`p-4 rounded-lg border-2 ${getSignalColor(prediction.recommendation.signal)}`}>                  )}

                  <div className="flex items-center justify-between mb-2">                  

                    <h3 className="text-lg font-bold">{prediction.recommendation.signal}</h3>                  {prediction.predictions.Transformer && (

                    <Badge variant="outline" className="text-xs">                    <div className="p-4 border rounded-lg bg-card">

                      {prediction.recommendation.confidence_pct.toFixed(1)}% Confidence                      <div className="flex items-center justify-between mb-2">

                    </Badge>                        <span className="font-semibold text-purple-600">Transformer Model</span>

                  </div>                        <Badge variant="outline" className="text-xs">

                  <p className="text-sm font-medium mb-1">{prediction.recommendation.action}</p>                          {prediction.predictions.Transformer.time_steps} days lookback

                  <p className="text-xs opacity-80">{prediction.recommendation.risk_level}</p>                        </Badge>

                  {prediction.recommendation.stop_loss_suggestion && (                      </div>

                    <p className="text-xs mt-2 font-semibold">                      <div className="grid grid-cols-3 gap-2 text-sm">

                      💡 Stop-Loss: {prediction.recommendation.stop_loss_suggestion}                        <div>

                    </p>                          <p className="text-muted-foreground">Prediction</p>

                  )}                          <p className="font-semibold">{prediction.predictions.Transformer.prediction.toFixed(4)}%</p>

                </div>                        </div>

                        <div>

                {/* Direction Prediction */}                          <p className="text-muted-foreground">Error</p>

                <Card>                          <p className="font-semibold">{prediction.predictions.Transformer.error.toFixed(4)}%</p>

                  <CardHeader className="pb-3">                        </div>

                    <CardTitle className="text-sm flex items-center gap-2">                        <div>

                      <TrendingUp className="w-4 h-4" />                          <p className="text-muted-foreground">Error %</p>

                      Direction Prediction                          <p className="font-semibold">{prediction.predictions.Transformer.error_pct.toFixed(2)}%</p>

                    </CardTitle>                        </div>

                  </CardHeader>                      </div>

                  <CardContent className="space-y-2">                    </div>

                    <div className="flex items-center justify-between">                  )}

                      <span className="text-2xl font-bold">{prediction.direction.label}</span>                </div>

                      <Badge variant={prediction.direction.label.includes("UP") ? "default" : "destructive"}>

                        {(prediction.direction.probability * 100).toFixed(1)}%                {/* Target Date Info */}

                      </Badge>                <div className="p-4 bg-muted/30 rounded-lg border">

                    </div>                  <p className="text-sm font-medium mb-2">Prediction Details</p>

                    <div className="grid grid-cols-2 gap-2 text-sm">                  <div className="space-y-1 text-sm text-muted-foreground">

                      <div>                    <p>• Target Date: {new Date(prediction.target_date).toLocaleDateString('vi-VN')}</p>

                        <p className="text-muted-foreground">Threshold</p>                    <p>• Models Used: {prediction.summary.models_used.join(', ')}</p>

                        <p className="font-semibold">{(prediction.direction.threshold * 100).toFixed(1)}%</p>                    <p>• Metric: Next-day price range (High-Low %) prediction</p>

                      </div>                  </div>

                      <div>                </div>

                        <p className="text-muted-foreground">Confidence</p>              </div>

                        <p className="font-semibold">{(prediction.direction.confidence * 100).toFixed(1)}%</p>            ) : null}

                      </div>          </CardContent>

                    </div>        </Card>

                    <p className="text-xs text-muted-foreground pt-2 border-t">      </div>

                      {prediction.direction.model}

                    </p>      {/* Additional Info */}

                  </CardContent>      <Card className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20 border-2">

                </Card>        <CardHeader>

          <CardTitle className="text-lg">How It Works</CardTitle>

                {/* Volatility Prediction */}        </CardHeader>

                <Card>        <CardContent className="space-y-2 text-sm text-muted-foreground">

                  <CardHeader className="pb-3">          <p>

                    <CardTitle className="text-sm flex items-center gap-2">            • <strong>AI Models:</strong> Uses advanced LSTM and Transformer models trained on Vietnamese stock market data

                      <BarChart3 className="w-4 h-4" />          </p>

                      Volatility Prediction          <p>

                    </CardTitle>            • <strong>Data Sources:</strong> Analyzes historical prices, trading volumes, news sentiment, and technical indicators

                  </CardHeader>          </p>

                  <CardContent className="space-y-2">          <p>

                    <div className="flex items-center justify-between">            • <strong>Accuracy:</strong> Models are continuously retrained and validated against recent market movements

                      <span className="text-muted-foreground">Expected Range</span>          </p>

                      <span className="text-2xl font-bold text-orange-600">          <p>

                        {prediction.volatility.predicted_range_pct.toFixed(2)}%            • <strong>Disclaimer:</strong> Predictions are for reference only and should not be used as sole basis for investment decisions

                      </span>          </p>

                    </div>        </CardContent>

                    <div className="text-sm space-y-1">      </Card>

                      <div className="flex justify-between">    </div>

                        <span className="text-muted-foreground">Estimated High</span>  );

                        <span className="font-semibold text-green-600">};

                          {prediction.price_forecast.estimated_high.toLocaleString()} VND

                        </span>export default ModelInference;

                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Estimated Low</span>
                        <span className="font-semibold text-red-600">
                          {prediction.price_forecast.estimated_low.toLocaleString()} VND
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground pt-2 border-t">
                      {prediction.volatility.model}
                    </p>
                  </CardContent>
                </Card>

                {/* Actual Results */}
                {prediction.actual.price && (
                  <Card className="bg-muted/30">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm flex items-center gap-2">
                        {prediction.accuracy.direction_correct ? (
                          <CheckCircle2 className="w-4 h-4 text-green-600" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-red-600" />
                        )}
                        Actual Results
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <p className="text-muted-foreground">Next Day Price</p>
                          <p className="font-semibold">{prediction.actual.price.toLocaleString()} VND</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Return</p>
                          <p className={`font-semibold ${
                            prediction.actual.return_pct! > 0 ? "text-green-600" : "text-red-600"
                          }`}>
                            {prediction.actual.return_pct! > 0 ? "+" : ""}
                            {prediction.actual.return_pct?.toFixed(2)}%
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Actual Range</p>
                          <p className="font-semibold">{prediction.actual.range_pct?.toFixed(2)}%</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Direction</p>
                          <p className="font-semibold">{prediction.actual.label}</p>
                        </div>
                      </div>
                      
                      <div className="pt-2 border-t space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Direction Accuracy</span>
                          <Badge variant={prediction.accuracy.direction_correct ? "default" : "destructive"}>
                            {prediction.accuracy.direction_correct ? "✓ Correct" : "✗ Incorrect"}
                          </Badge>
                        </div>
                        {prediction.accuracy.range_error_pct !== null && (
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Range Error</span>
                            <span className="font-semibold">
                              {prediction.accuracy.range_error_pct.toFixed(2)}%
                            </span>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Metadata */}
                <div className="p-3 bg-muted/30 rounded-lg border text-xs space-y-1">
                  <p><strong>Ticker:</strong> {prediction.ticker}</p>
                  <p><strong>Target Date:</strong> {new Date(prediction.target_date).toLocaleDateString('vi-VN')}</p>
                  <p><strong>Current Price:</strong> {prediction.current_price.toLocaleString()} VND</p>
                  <p><strong>Timestamp:</strong> {new Date(prediction.timestamp).toLocaleString('vi-VN')}</p>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {/* Model Info Card */}
      <Card className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20 border-2">
        <CardHeader>
          <CardTitle className="text-lg">Dual-Model Architecture</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <h4 className="font-semibold flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Direction Model
              </h4>
              <ul className="space-y-1 text-muted-foreground">
                <li>• Bi-LSTM (64→32 units)</li>
                <li>• 44 features (38 tech + 6 news)</li>
                <li>• UP/DOWN with probability</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                Volatility Model
              </h4>
              <ul className="space-y-1 text-muted-foreground">
                <li>• Bi-LSTM (128→128 units)</li>
                <li>• 38 technical indicators</li>
                <li>• Price range % prediction</li>
              </ul>
            </div>
          </div>
          
          {modelInfo && (
            <div className="pt-3 border-t">
              <h4 className="font-semibold mb-2">Model Performance</h4>
              <div className="grid grid-cols-5 gap-2 text-xs">
                {Object.entries(modelInfo.performance).map(([ticker, perf]: [string, any]) => (
                  <div key={ticker} className="p-2 bg-background rounded border">
                    <p className="font-semibold">{ticker}</p>
                    <p className="text-muted-foreground">Acc: {perf.accuracy}</p>
                    <p className="text-muted-foreground">F1: {perf.f1}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <Alert className="mt-4">
            <Info className="h-4 w-4" />
            <AlertDescription>
              <strong>Signal Strength:</strong>
              <br />🟢 Strong (&gt;70%): Aggressive trading
              <br />🟡 Moderate (50-70%): Conservative with stop-loss
              <br />⚪ Hold (&lt;50%): Wait for stronger signals
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    </div>
  );
};

export default ModelInference;
