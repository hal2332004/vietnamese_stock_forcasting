import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  Bot, 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  DollarSign,
  Target,
  AlertCircle,
  RefreshCw,
  Play,
  BarChart3,
  LineChart,
  CheckCircle,
  XCircle,
  Clock
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";

// API Configuration
const API_BASE_URL = "http://localhost:8000";

interface TradingRequest {
  ticker: string;
  days: number;
  initial_capital: number;
  mode: string;
  model_type: string;  // PPO or SAC
  sentiment_threshold: number;
  confidence_threshold: number;
  max_position: number;
  stochastic: boolean;  // Use stochastic sampling for PPO
}

interface TradingStatus {
  session_id: string;
  status: string;
  ticker: string;
  model_type?: string;  // Model type (PPO or SAC)
  progress: number;
  total_days: number;
  current_return: number;
  trades_count: number;
  start_time: string;
  end_time?: string;
  error?: string;
}

interface Trade {
  timestamp: string;
  action: string;
  price: number;
  shares: number;
  cost?: number;
  proceeds?: number;
  sentiment: {
    sentiment_mean: number;
    sentiment_std: number;
    news_count: number;
    positive_mean: number;
    negative_mean: number;
    confidence: number;
  };
  cash_after: number;
  position_value: number;
}

interface TradingResults {
  session_id: string;
  status: string;
  request: TradingRequest;
  trades: Trade[];
  portfolio_values: any[];
  final_value: number;
  total_return: number;
  start_time: string;
  end_time: string;
  error?: string;
}

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

const RLInference = () => {
  // Form state
  const [ticker, setTicker] = useState("FPT");
  const [modelType, setModelType] = useState("PPO");  // PPO or SAC
  const [days, setDays] = useState(30);
  const [capital, setCapital] = useState(100000000);
  const [maxPosition, setMaxPosition] = useState(0.5);
  const [sentimentThreshold, setSentimentThreshold] = useState(-0.5);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.0);
  const [stochastic, setStochastic] = useState(true);  // Stochastic sampling for PPO
  
  // Trading state
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [status, setStatus] = useState<TradingStatus | null>(null);
  const [results, setResults] = useState<TradingResults | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  
  // WebSocket
  const wsRef = useRef<WebSocket | null>(null);
  const statusIntervalRef = useRef<number | null>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);

  // Available tickers
  const [tickers, setTickers] = useState<string[]>(["FPT", "ACB", "VCB", "MBB", "BID"]);

  // Connect to WebSocket for real-time logs
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
      }
    };
  }, []);

  // Auto-scroll logs
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const connectWebSocket = () => {
    const ws = new WebSocket('ws://localhost:8000/ws/logs');
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      addLog('Connected to real-time logs', 'SUCCESS');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type !== 'ping') {
        addLog(data.message, data.level);
      }
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      addLog('Disconnected from logs. Reconnecting...', 'WARNING');
      setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    wsRef.current = ws;
  };

  const addLog = (message: string, level: string = 'INFO') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, { timestamp, level, message }]);
  };

  const fetchTickers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/tickers`);
      if (response.ok) {
        const data = await response.json();
        setTickers(data.tickers);
      }
    } catch (error) {
      console.error("Error fetching tickers:", error);
    }
  };

  const startTrading = async () => {
    setIsRunning(true);
    setLogs([]);
    setResults(null);
    setStatus(null);
    
    const request: TradingRequest = {
      ticker,
      days,
      initial_capital: capital,
      mode: "paper",
      model_type: modelType,
      sentiment_threshold: sentimentThreshold,
      confidence_threshold: confidenceThreshold,
      max_position: maxPosition,
      stochastic: stochastic  // Use stochastic sampling for PPO
    };

    try {
      const response = await fetch(`${API_BASE_URL}/api/trading/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error("Failed to start trading session");
      }

      const data = await response.json();
      setCurrentSession(data.session_id);
      toast.success(`Trading session started: ${data.session_id}`);
      
      // Start polling for status
      startStatusPolling(data.session_id);
      
    } catch (error: any) {
      console.error("Error starting trading:", error);
      toast.error(error.message || "Failed to start trading session");
      setIsRunning(false);
    }
  };

  const startStatusPolling = (sessionId: string) => {
    // Clear existing interval
    if (statusIntervalRef.current) {
      clearInterval(statusIntervalRef.current);
    }

    // Poll every second
    statusIntervalRef.current = window.setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/trading/status/${sessionId}`);
        if (!response.ok) throw new Error("Failed to fetch status");
        
        const statusData: TradingStatus = await response.json();
        setStatus(statusData);
        
        // If completed or failed, stop polling and load results
        if (statusData.status === 'completed' || statusData.status === 'failed') {
          if (statusIntervalRef.current) {
            clearInterval(statusIntervalRef.current);
          }
          setIsRunning(false);
          
          if (statusData.status === 'completed') {
            toast.success('Trading session completed successfully!');
            await loadResults(sessionId);
          } else {
            toast.error(`Trading session failed: ${statusData.error}`);
          }
        }
        
      } catch (error) {
        console.error("Error fetching status:", error);
      }
    }, 1000);
  };

  const loadResults = async (sessionId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/trading/results/${sessionId}`);
      if (!response.ok) throw new Error("Failed to fetch results");
      
      const resultsData: TradingResults = await response.json();
      setResults(resultsData);
      
    } catch (error: any) {
      console.error("Error loading results:", error);
      toast.error(error.message || "Failed to load results");
    }
  };

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { 
      style: 'currency', 
      currency: 'VND',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatPercent = (value: number) => {
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getLogColor = (level: string) => {
    switch (level) {
      case 'INFO': return 'text-blue-400';
      case 'SUCCESS': return 'text-green-400';
      case 'WARNING': return 'text-yellow-400';
      case 'ERROR': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
          <Bot className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-foreground">RL Trading Inference</h1>
          <p className="text-muted-foreground">
            Reinforcement Learning agent with sentiment analysis
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <Card className="border-2 lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5 text-primary" />
              Trading Configuration
            </CardTitle>
            <CardDescription>
              Configure RL agent parameters
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Model Selection */}
            <div className="space-y-2">
              <Label htmlFor="model-select">RL Algorithm</Label>
              <Select value={modelType} onValueChange={setModelType} disabled={isRunning}>
                <SelectTrigger id="model-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PPO">
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4" />
                      <div>
                        <div className="font-semibold">PPO</div>
                        <div className="text-xs text-muted-foreground">Proximal Policy Optimization</div>
                      </div>
                    </div>
                  </SelectItem>
                  <SelectItem value="SAC">
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4" />
                      <div>
                        <div className="font-semibold">SAC</div>
                        <div className="text-xs text-muted-foreground">Soft Actor-Critic</div>
                      </div>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {modelType === "PPO" ? 
                  "On-policy algorithm with clipped objective (more stable)" :
                  "Off-policy algorithm with entropy regularization (better exploration)"
                }
              </p>
            </div>

            {/* Ticker Selection */}
            <div className="space-y-2">
              <Label htmlFor="ticker-select">Stock Ticker</Label>
              <Select value={ticker} onValueChange={setTicker} disabled={isRunning}>
                <SelectTrigger id="ticker-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {tickers.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Trading Days */}
            <div className="space-y-2">
              <Label htmlFor="days-input">Trading Days</Label>
              <Input
                id="days-input"
                type="number"
                value={days}
                onChange={(e) => setDays(parseInt(e.target.value))}
                min={1}
                max={365}
                disabled={isRunning}
              />
            </div>

            {/* Initial Capital */}
            <div className="space-y-2">
              <Label htmlFor="capital-input">Initial Capital (VND)</Label>
              <Input
                id="capital-input"
                type="number"
                value={capital}
                onChange={(e) => setCapital(parseFloat(e.target.value))}
                min={1000000}
                step={1000000}
                disabled={isRunning}
              />
              <p className="text-xs text-muted-foreground">
                {formatVND(capital)}
              </p>
            </div>

            {/* Max Position */}
            <div className="space-y-2">
              <Label htmlFor="position-input">Max Position (0-1)</Label>
              <Input
                id="position-input"
                type="number"
                value={maxPosition}
                onChange={(e) => setMaxPosition(parseFloat(e.target.value))}
                min={0.1}
                max={1.0}
                step={0.1}
                disabled={isRunning}
              />
              <p className="text-xs text-muted-foreground">
                {(maxPosition * 100).toFixed(0)}% of portfolio
              </p>
            </div>

            {/* Sentiment Threshold */}
            <div className="space-y-2">
              <Label htmlFor="sentiment-input">Sentiment Threshold</Label>
              <Input
                id="sentiment-input"
                type="number"
                value={sentimentThreshold}
                onChange={(e) => setSentimentThreshold(parseFloat(e.target.value))}
                min={-1}
                max={1}
                step={0.1}
                disabled={isRunning}
              />
            </div>

            {/* Confidence Threshold */}
            <div className="space-y-2">
              <Label htmlFor="confidence-input">Confidence Threshold</Label>
              <Input
                id="confidence-input"
                type="number"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                min={0}
                max={1}
                step={0.1}
                disabled={isRunning}
              />
            </div>

            {/* Stochastic Sampling (PPO only) */}
            {modelType === "PPO" && (
              <div className="flex items-center space-x-3 p-3 bg-muted/50 rounded-lg">
                <input
                  id="stochastic-checkbox"
                  type="checkbox"
                  checked={stochastic}
                  onChange={(e) => setStochastic(e.target.checked)}
                  disabled={isRunning}
                  className="w-4 h-4 text-primary cursor-pointer"
                />
                <div className="flex-1">
                  <Label 
                    htmlFor="stochastic-checkbox" 
                    className="cursor-pointer font-medium"
                  >
                    Stochastic Sampling
                  </Label>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Sample from probability distribution instead of always choosing highest probability action. Helps prevent constant HOLD behavior.
                  </p>
                </div>
              </div>
            )}

            {/* Start Button */}
            <Button 
              onClick={startTrading}
              disabled={isRunning}
              className="w-full h-12 text-base gap-2"
              size="lg"
            >
              {isRunning ? (
                <>
                  <Activity className="w-5 h-5 animate-spin" />
                  Trading in Progress...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  Start Trading
                </>
              )}
            </Button>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                <strong>Note:</strong> Ensure API server is running
                <br />
                <code className="text-xs bg-muted px-1 py-0.5 rounded">
                  python api_server.py
                </code>
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* Status & Results Panel */}
        <div className="lg:col-span-2 space-y-6">
          {/* Status Card */}
          {status && (
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-primary" />
                  Trading Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Progress Bar */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="font-medium">
                      {status.progress}/{status.total_days} days
                    </span>
                  </div>
                  <Progress 
                    value={(status.progress / status.total_days) * 100} 
                    className="h-3"
                  />
                </div>

                {/* Status Grid */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="p-3 border rounded-lg bg-card">
                    <p className="text-xs text-muted-foreground mb-1">Model</p>
                    <Badge variant="outline" className="text-sm font-bold">
                      {status.model_type || modelType}
                    </Badge>
                  </div>

                  <div className="p-3 border rounded-lg bg-card">
                    <p className="text-xs text-muted-foreground mb-1">Status</p>
                    <Badge variant={
                      status.status === 'completed' ? 'default' : 
                      status.status === 'failed' ? 'destructive' : 'secondary'
                    }>
                      {status.status.toUpperCase()}
                    </Badge>
                  </div>

                  <div className="p-3 border rounded-lg bg-card">
                    <p className="text-xs text-muted-foreground mb-1">Ticker</p>
                    <p className="text-lg font-bold">{status.ticker}</p>
                  </div>

                  <div className="p-3 border rounded-lg bg-card">
                    <p className="text-xs text-muted-foreground mb-1">Return</p>
                    <p className={`text-lg font-bold ${
                      status.current_return >= 0 ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {formatPercent(status.current_return)}
                    </p>
                  </div>

                  <div className="p-3 border rounded-lg bg-card">
                    <p className="text-xs text-muted-foreground mb-1">Trades</p>
                    <p className="text-lg font-bold">{status.trades_count}</p>
                  </div>
                </div>

                {/* Session Info */}
                <div className="p-3 bg-muted/30 rounded-lg text-xs">
                  <p className="font-medium mb-1">Session: {status.session_id}</p>
                  <p className="text-muted-foreground">
                    Started: {new Date(status.start_time).toLocaleString('vi-VN')}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Results Card */}
          {results && (
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-primary" />
                  Trading Results
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="p-4 border rounded-lg bg-gradient-to-br from-background to-muted">
                    <div className="flex items-center gap-2 mb-2">
                      <DollarSign className="w-4 h-4 text-muted-foreground" />
                      <p className="text-xs text-muted-foreground">Initial Capital</p>
                    </div>
                    <p className="text-lg font-bold">
                      {formatVND(results.request.initial_capital)}
                    </p>
                  </div>

                  <div className="p-4 border rounded-lg bg-gradient-to-br from-background to-muted">
                    <div className="flex items-center gap-2 mb-2">
                      <DollarSign className="w-4 h-4 text-muted-foreground" />
                      <p className="text-xs text-muted-foreground">Final Value</p>
                    </div>
                    <p className="text-lg font-bold">
                      {formatVND(results.final_value)}
                    </p>
                  </div>

                  <div className="p-4 border rounded-lg bg-gradient-to-br from-background to-muted">
                    <div className="flex items-center gap-2 mb-2">
                      {results.total_return >= 0 ? (
                        <TrendingUp className="w-4 h-4 text-green-500" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-500" />
                      )}
                      <p className="text-xs text-muted-foreground">Total Return</p>
                    </div>
                    <p className={`text-2xl font-bold ${
                      results.total_return >= 0 ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {formatPercent(results.total_return)}
                    </p>
                  </div>
                </div>

                {/* Trades Table */}
                {results.trades && results.trades.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="font-semibold text-sm">Trade History</h3>
                    <div className="border rounded-lg overflow-hidden">
                      <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-muted sticky top-0">
                            <tr>
                              <th className="text-left p-2">Time</th>
                              <th className="text-left p-2">Action</th>
                              <th className="text-right p-2">Price</th>
                              <th className="text-right p-2">Shares</th>
                              <th className="text-right p-2">Amount</th>
                              <th className="text-right p-2">Sentiment</th>
                            </tr>
                          </thead>
                          <tbody>
                            {results.trades
                              .filter(t => ['BUY', 'SELL'].includes(t.action))
                              .map((trade, idx) => (
                              <tr key={idx} className="border-t hover:bg-muted/50">
                                <td className="p-2">
                                  {new Date(trade.timestamp).toLocaleTimeString('vi-VN')}
                                </td>
                                <td className="p-2">
                                  <Badge 
                                    variant={trade.action === 'BUY' ? 'default' : 'destructive'}
                                    className="text-xs"
                                  >
                                    {trade.action === 'BUY' ? (
                                      <><CheckCircle className="w-3 h-3 mr-1" /> BUY</>
                                    ) : (
                                      <><XCircle className="w-3 h-3 mr-1" /> SELL</>
                                    )}
                                  </Badge>
                                </td>
                                <td className="p-2 text-right font-mono">
                                  {trade.price.toLocaleString()} đ
                                </td>
                                <td className="p-2 text-right font-mono">
                                  {trade.shares?.toLocaleString()}
                                </td>
                                <td className="p-2 text-right font-mono">
                                  {formatVND((trade.cost || trade.proceeds || 0))}
                                </td>
                                <td className="p-2 text-right">
                                  <span className={`font-medium ${
                                    trade.sentiment.sentiment_mean > 0 ? 'text-green-500' : 'text-red-500'
                                  }`}>
                                    {trade.sentiment.sentiment_mean.toFixed(3)}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Logs Card */}
          <Card className="border-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LineChart className="w-5 h-5 text-primary" />
                Real-Time Trading Logs
              </CardTitle>
              <CardDescription>
                Live updates from the trading agent
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div 
                ref={logsContainerRef}
                className="bg-slate-950 rounded-lg p-4 h-[400px] overflow-y-auto font-mono text-xs space-y-1"
              >
                {logs.length === 0 ? (
                  <p className="text-slate-500">Waiting for trading session to start...</p>
                ) : (
                  logs.map((log, idx) => (
                    <div key={idx} className={getLogColor(log.level)}>
                      <span className="text-slate-600">[{log.timestamp}]</span>{' '}
                      <span className="font-semibold">[{log.level}]</span>{' '}
                      {log.message}
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Info Card */}
      <Card className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20 border-2">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Bot className="w-5 h-5" />
            About RL Trading Agents
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <div>
            <strong className="text-foreground">🤖 PPO (Proximal Policy Optimization):</strong>
            <ul className="list-disc list-inside ml-2 mt-1 space-y-1">
              <li>On-policy algorithm with clipped surrogate objective</li>
              <li>More stable training, good for continuous learning</li>
              <li>Uses GAE (Generalized Advantage Estimation)</li>
              <li>Best for: Conservative, stable trading strategies</li>
            </ul>
          </div>
          
          <div>
            <strong className="text-foreground">🎯 SAC (Soft Actor-Critic):</strong>
            <ul className="list-disc list-inside ml-2 mt-1 space-y-1">
              <li>Off-policy with maximum entropy framework</li>
              <li>Better sample efficiency, automatic exploration tuning</li>
              <li>Two Q-networks to reduce overestimation bias</li>
              <li>Best for: Aggressive exploration, diverse strategies</li>
            </ul>
          </div>
          
          <div className="pt-2 border-t">
            <p>
              • <strong>State Features:</strong> Portfolio (5) + Technical indicators (15) + Sentiment scores (5) = 25 dimensions
            </p>
            <p>
              • <strong>Actions:</strong> HOLD, BUY, or SELL based on market conditions and sentiment
            </p>
            <p>
              • <strong>Risk Management:</strong> Position sizing, transaction costs, and sentiment-based filters
            </p>
            <p className="text-xs mt-2 text-orange-600 dark:text-orange-400">
              ⚠️ <strong>Disclaimer:</strong> This is a research tool for paper trading only. Not financial advice.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default RLInference;
