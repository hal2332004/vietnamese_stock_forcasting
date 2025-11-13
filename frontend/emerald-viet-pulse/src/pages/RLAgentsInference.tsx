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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  Play,
  BarChart3,
  CheckCircle,
  XCircle,
  Zap,
  GitCompare,
  Clock
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";

// API Configuration
const API_BASE_URL = "http://localhost:8001";

interface InferenceRequest {
  ticker: string;
  agent_type: "ppo" | "sac";
  days: number;
  initial_capital: number;
  deterministic: boolean;
  verbose: boolean;
}

interface ComparisonRequest {
  ticker: string;
  days: number;
  initial_capital: number;
}

interface SessionStatus {
  session_id: string;
  status: string;
  agent_type: string;
  ticker: string;
  progress: number;
  total_days: number;
  current_return?: number;
  num_trades?: number;
  start_time: string;
  end_time?: string;
  error?: string;
}

interface Trade {
  step?: number;
  type: "BUY" | "SELL";
  shares: number;
  price: number;
  cost?: number;
  revenue?: number;
  total?: number;
  timestamp?: string;
}

interface InferenceResults {
  agent_type: string;
  ticker: string;
  days_traded: number;
  initial_capital: number;
  final_value: number;
  total_return_pct: number;
  num_trades: number;
  buy_trades: number;
  sell_trades: number;
  trades: Trade[];
  portfolio_values: number[];
}

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  logger: string;
}

const RLAgentsInference = () => {
  // Form state
  const [ticker, setTicker] = useState("FPT");
  const [agentType, setAgentType] = useState<"ppo" | "sac">("ppo");
  const [days, setDays] = useState(30);
  const [capital, setCapital] = useState(100000000);
  const [deterministic, setDeterministic] = useState(false); // Stochastic by default
  const [mode, setMode] = useState<"single" | "compare">("single");
  
  // Session state
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [status, setStatus] = useState<SessionStatus | null>(null);
  const [results, setResults] = useState<any>(null);
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
    fetchTickers();
    
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
    try {
      const ws = new WebSocket(`ws://localhost:8001/ws/logs`);
      
      ws.onopen = () => {
        console.log("WebSocket connected");
        addLog({
          timestamp: new Date().toISOString(),
          level: "INFO",
          message: "Connected to RL Agents inference server",
          logger: "client"
        });
      };
      
      ws.onmessage = (event) => {
        try {
          const log = JSON.parse(event.data);
          if (log.type !== "ping" && log.type !== "pong") {
            addLog(log);
          }
        } catch (e) {
          console.error("Failed to parse log:", e);
        }
      };
      
      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
      
      ws.onclose = () => {
        console.log("WebSocket disconnected");
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };
      
      wsRef.current = ws;
    } catch (error) {
      console.error("Failed to connect WebSocket:", error);
    }
  };

  const addLog = (log: LogEntry) => {
    setLogs(prev => [...prev.slice(-100), log]); // Keep last 100 logs
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

  const startInference = async () => {
    setIsRunning(true);
    setLogs([]);
    setResults(null);
    setStatus(null);
    
    try {
      let endpoint = "";
      let requestBody: any = {};
      
      if (mode === "single") {
        endpoint = `${API_BASE_URL}/api/inference`;
        requestBody = {
          ticker,
          agent_type: agentType,
          days,
          initial_capital: capital,
          deterministic,
          verbose: true
        };
      } else {
        endpoint = `${API_BASE_URL}/api/compare`;
        requestBody = {
          ticker,
          days,
          initial_capital: capital
        };
      }

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error("Failed to start inference");
      }

      const data = await response.json();
      setCurrentSession(data.session_id);
      toast.success(`${mode === "single" ? agentType.toUpperCase() : "Comparison"} inference started!`);
      
      // Start polling for status
      startStatusPolling(data.session_id);
      
    } catch (error: any) {
      console.error("Error starting inference:", error);
      toast.error(error.message || "Failed to start inference");
      setIsRunning(false);
    }
  };

  const startStatusPolling = (sessionId: string) => {
    // Clear existing interval
    if (statusIntervalRef.current) {
      clearInterval(statusIntervalRef.current);
    }
    
    // Poll every 2 seconds
    statusIntervalRef.current = window.setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/status/${sessionId}`);
        if (!response.ok) {
          throw new Error("Failed to fetch status");
        }
        
        const statusData: SessionStatus = await response.json();
        setStatus(statusData);
        
        // If completed or failed, fetch results and stop polling
        if (statusData.status === "completed" || statusData.status === "failed") {
          clearInterval(statusIntervalRef.current!);
          statusIntervalRef.current = null;
          setIsRunning(false);
          
          if (statusData.status === "completed") {
            fetchResults(sessionId);
            toast.success("Inference completed!");
          } else {
            toast.error(`Inference failed: ${statusData.error}`);
          }
        }
      } catch (error) {
        console.error("Error fetching status:", error);
      }
    }, 2000);
  };

  const fetchResults = async (sessionId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/results/${sessionId}`);
      if (!response.ok) {
        throw new Error("Failed to fetch results");
      }
      
      const data = await response.json();
      setResults(data.results);
    } catch (error) {
      console.error("Error fetching results:", error);
      toast.error("Failed to fetch results");
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

  const formatTimestamp = (timestamp?: string, step?: number) => {
    if (timestamp) {
      try {
        const date = new Date(timestamp);
        if (!isNaN(date.getTime())) {
          return date.toLocaleString('vi-VN');
        }
      } catch (e) {
        // Invalid timestamp, fall through to step
      }
    }
    return step !== undefined ? `Day ${step}` : 'N/A';
  };

  const getLogColor = (level: string) => {
    switch (level) {
      case "ERROR": return "text-red-500";
      case "WARNING": return "text-yellow-500";
      case "INFO": return "text-blue-500";
      case "SUCCESS": return "text-green-500";
      default: return "text-muted-foreground";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
          <Bot className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-foreground">RL Agents Inference</h1>
          <p className="text-muted-foreground">
            Advanced reinforcement learning trading agents (PPO & SAC)
          </p>
        </div>
      </div>

      {/* Mode Selection */}
      <Card className="border-2">
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <Label className="text-base font-medium">Inference Mode:</Label>
            <Tabs value={mode} onValueChange={(v) => setMode(v as "single" | "compare")} className="flex-1">
              <TabsList className="grid w-full max-w-md grid-cols-2">
                <TabsTrigger value="single" className="gap-2">
                  <Zap className="w-4 h-4" />
                  Single Agent
                </TabsTrigger>
                <TabsTrigger value="compare" className="gap-2">
                  <GitCompare className="w-4 h-4" />
                  Compare (PPO vs SAC)
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <Card className="border-2 lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5 text-primary" />
              Configuration
            </CardTitle>
            <CardDescription>
              Set up inference parameters
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
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

            {/* Agent Type (only for single mode) */}
            {mode === "single" && (
              <div className="space-y-2">
                <Label htmlFor="agent-select">Agent Type</Label>
                <Select 
                  value={agentType} 
                  onValueChange={(v) => setAgentType(v as "ppo" | "sac")}
                  disabled={isRunning}
                >
                  <SelectTrigger id="agent-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ppo">
                      <div className="flex items-center gap-2">
                        <Bot className="w-4 h-4 text-blue-500" />
                        <span>PPO (Proximal Policy Optimization)</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="sac">
                      <div className="flex items-center gap-2">
                        <Bot className="w-4 h-4 text-purple-500" />
                        <span>SAC (Soft Actor-Critic)</span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

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

            {/* Deterministic/Stochastic (only for single mode with PPO) */}
            {mode === "single" && agentType === "ppo" && (
              <div className="flex items-center space-x-3 p-3 bg-muted/50 rounded-lg">
                <input
                  id="deterministic-checkbox"
                  type="checkbox"
                  checked={!deterministic}
                  onChange={(e) => setDeterministic(!e.target.checked)}
                  disabled={isRunning}
                  className="w-4 h-4 text-primary cursor-pointer"
                />
                <div className="flex-1">
                  <Label 
                    htmlFor="deterministic-checkbox" 
                    className="cursor-pointer font-medium"
                  >
                    Stochastic Sampling
                  </Label>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Sample from probability distribution for exploration
                  </p>
                </div>
              </div>
            )}

            {/* Start Button */}
            <Button 
              onClick={startInference}
              disabled={isRunning}
              className="w-full h-12 text-base gap-2"
              size="lg"
            >
              {isRunning ? (
                <>
                  <Activity className="w-5 h-5 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  Start {mode === "single" ? "Inference" : "Comparison"}
                </>
              )}
            </Button>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                <strong>Note:</strong> API server must be running on localhost:8001
                <br />
                <code className="text-xs bg-muted px-1 py-0.5 rounded">
                  python api_rl_inference.py
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
                  Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant={
                      status.status === "completed" ? "default" :
                      status.status === "failed" ? "destructive" :
                      "secondary"
                    }>
                      {status.status === "completed" ? (
                        <CheckCircle className="w-3 h-3 mr-1" />
                      ) : status.status === "failed" ? (
                        <XCircle className="w-3 h-3 mr-1" />
                      ) : (
                        <Activity className="w-3 h-3 mr-1 animate-spin" />
                      )}
                      {status.status.toUpperCase()}
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      {status.agent_type?.toUpperCase() || "COMPARISON"}
                    </span>
                  </div>
                  <span className="text-sm font-medium">
                    Day {status.progress} / {status.total_days}
                  </span>
                </div>
                
                <Progress value={(status.progress / status.total_days) * 100} className="h-2" />
                
                {status.current_return !== undefined && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-muted/50 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-1">Current Return</p>
                      <p className={`text-xl font-bold ${
                        status.current_return > 0 ? "text-green-500" : "text-red-500"
                      }`}>
                        {formatPercent(status.current_return)}
                      </p>
                    </div>
                    <div className="p-3 bg-muted/50 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-1">Trades</p>
                      <p className="text-xl font-bold">{status.num_trades}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Results Card */}
          {results && mode === "single" && (
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-primary" />
                  Results
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 border rounded-lg bg-card">
                    <div className="flex items-center gap-2 mb-2">
                      <DollarSign className="w-4 h-4 text-muted-foreground" />
                      <p className="text-xs text-muted-foreground">Final Value</p>
                    </div>
                    <p className="text-lg font-bold">{formatVND(results.final_value)}</p>
                  </div>
                  
                  <div className="p-4 border rounded-lg bg-card">
                    <div className="flex items-center gap-2 mb-2">
                      {results.total_return_pct > 0 ? (
                        <TrendingUp className="w-4 h-4 text-green-500" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-500" />
                      )}
                      <p className="text-xs text-muted-foreground">Total Return</p>
                    </div>
                    <p className={`text-lg font-bold ${
                      results.total_return_pct > 0 ? "text-green-500" : "text-red-500"
                    }`}>
                      {formatPercent(results.total_return_pct)}
                    </p>
                  </div>
                  
                  <div className="p-4 border rounded-lg bg-card">
                    <div className="flex items-center gap-2 mb-2">
                      <Activity className="w-4 h-4 text-muted-foreground" />
                      <p className="text-xs text-muted-foreground">Total Trades</p>
                    </div>
                    <p className="text-lg font-bold">{results.num_trades}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {results.buy_trades} Buy / {results.sell_trades} Sell
                    </p>
                  </div>
                  
                  <div className="p-4 border rounded-lg bg-card">
                    <div className="flex items-center gap-2 mb-2">
                      <Clock className="w-4 h-4 text-muted-foreground" />
                      <p className="text-xs text-muted-foreground">Hold Days</p>
                    </div>
                    <p className="text-lg font-bold">
                      {results.days_traded - results.num_trades}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {(((results.days_traded - results.num_trades) / results.days_traded) * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>

                {/* Trade History */}
                <div className="space-y-2">
                  <h4 className="font-semibold text-sm">Recent Trades</h4>
                  <div className="max-h-60 overflow-y-auto space-y-2 border rounded-lg p-3">
                    {results.trades?.slice(-10).reverse().map((trade: Trade, idx: number) => (
                      <div 
                        key={idx} 
                        className="flex items-center justify-between p-2 bg-muted/30 rounded text-sm"
                      >
                        <div className="flex items-center gap-2">
                          <Badge variant={trade.type === "BUY" ? "default" : "destructive"}>
                            {trade.type}
                          </Badge>
                          <span>{trade.shares} shares</span>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold">{formatVND(trade.price)}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatTimestamp(trade.timestamp, trade.step)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Comparison Results */}
          {results && mode === "compare" && (
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GitCompare className="w-5 h-5 text-primary" />
                  Comparison Results
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* PPO Results */}
                  {results.ppo && (
                    <div className="p-4 border-2 border-blue-500/20 rounded-lg bg-blue-50/50 dark:bg-blue-950/20">
                      <div className="flex items-center gap-2 mb-4">
                        <Bot className="w-5 h-5 text-blue-500" />
                        <h4 className="font-bold text-blue-600 dark:text-blue-400">PPO Agent</h4>
                      </div>
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs text-muted-foreground">Return</p>
                          <p className={`text-2xl font-bold ${
                            results.ppo.total_return_pct > 0 ? "text-green-500" : "text-red-500"
                          }`}>
                            {formatPercent(results.ppo.total_return_pct)}
                          </p>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <p className="text-xs text-muted-foreground">Trades</p>
                            <p className="font-semibold">{results.ppo.num_trades}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Hold Days</p>
                            <p className="font-semibold">
                              {results.ppo.days_traded - results.ppo.num_trades} 
                              <span className="text-xs text-muted-foreground ml-1">
                                ({(((results.ppo.days_traded - results.ppo.num_trades) / results.ppo.days_traded) * 100).toFixed(0)}%)
                              </span>
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* SAC Results */}
                  {results.sac && (
                    <div className="p-4 border-2 border-purple-500/20 rounded-lg bg-purple-50/50 dark:bg-purple-950/20">
                      <div className="flex items-center gap-2 mb-4">
                        <Bot className="w-5 h-5 text-purple-500" />
                        <h4 className="font-bold text-purple-600 dark:text-purple-400">SAC Agent</h4>
                      </div>
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs text-muted-foreground">Return</p>
                          <p className={`text-2xl font-bold ${
                            results.sac.total_return_pct > 0 ? "text-green-500" : "text-red-500"
                          }`}>
                            {formatPercent(results.sac.total_return_pct)}
                          </p>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <p className="text-xs text-muted-foreground">Trades</p>
                            <p className="font-semibold">{results.sac.num_trades}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Hold Days</p>
                            <p className="font-semibold">
                              {results.sac.days_traded - results.sac.num_trades}
                              <span className="text-xs text-muted-foreground ml-1">
                                ({(((results.sac.days_traded - results.sac.num_trades) / results.sac.days_traded) * 100).toFixed(0)}%)
                              </span>
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Winner Badge */}
                {results.ppo && results.sac && (
                  <>
                    <div className="text-center p-4 bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-950/20 dark:to-orange-950/20 rounded-lg border-2 border-yellow-500/20">
                      <p className="text-sm text-muted-foreground mb-2">Winner</p>
                      <p className="text-2xl font-bold">
                        {results.ppo.total_return_pct > results.sac.total_return_pct ? (
                          <span className="text-blue-600 dark:text-blue-400">🏆 PPO</span>
                        ) : (
                          <span className="text-purple-600 dark:text-purple-400">🏆 SAC</span>
                        )}
                      </p>
                    </div>

                    {/* Detailed Comparison Table */}
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left p-2 font-medium text-muted-foreground">Metric</th>
                            <th className="text-right p-2 font-medium text-blue-600">PPO</th>
                            <th className="text-right p-2 font-medium text-purple-600">SAC</th>
                            <th className="text-center p-2 font-medium text-muted-foreground">Better</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          <tr>
                            <td className="p-2">Total Return</td>
                            <td className="text-right p-2 font-semibold">
                              {formatPercent(results.ppo.total_return_pct)}
                            </td>
                            <td className="text-right p-2 font-semibold">
                              {formatPercent(results.sac.total_return_pct)}
                            </td>
                            <td className="text-center p-2">
                              {results.ppo.total_return_pct > results.sac.total_return_pct ? '🔵' : '🟣'}
                            </td>
                          </tr>
                          <tr>
                            <td className="p-2">Total Trades</td>
                            <td className="text-right p-2">{results.ppo.num_trades}</td>
                            <td className="text-right p-2">{results.sac.num_trades}</td>
                            <td className="text-center p-2">-</td>
                          </tr>
                          <tr>
                            <td className="p-2">Hold Days</td>
                            <td className="text-right p-2">
                              {results.ppo.days_traded - results.ppo.num_trades} 
                              ({(((results.ppo.days_traded - results.ppo.num_trades) / results.ppo.days_traded) * 100).toFixed(0)}%)
                            </td>
                            <td className="text-right p-2">
                              {results.sac.days_traded - results.sac.num_trades}
                              ({(((results.sac.days_traded - results.sac.num_trades) / results.sac.days_traded) * 100).toFixed(0)}%)
                            </td>
                            <td className="text-center p-2">-</td>
                          </tr>
                          <tr>
                            <td className="p-2">Final Value</td>
                            <td className="text-right p-2">{formatVND(results.ppo.final_value)}</td>
                            <td className="text-right p-2">{formatVND(results.sac.final_value)}</td>
                            <td className="text-center p-2">
                              {results.ppo.final_value > results.sac.final_value ? '🔵' : '🟣'}
                            </td>
                          </tr>
                          <tr>
                            <td className="p-2">Buy Trades</td>
                            <td className="text-right p-2">{results.ppo.buy_trades}</td>
                            <td className="text-right p-2">{results.sac.buy_trades}</td>
                            <td className="text-center p-2">-</td>
                          </tr>
                          <tr>
                            <td className="p-2">Sell Trades</td>
                            <td className="text-right p-2">{results.ppo.sell_trades}</td>
                            <td className="text-right p-2">{results.sac.sell_trades}</td>
                            <td className="text-center p-2">-</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Live Logs */}
          <Card className="border-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary" />
                Live Logs
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div 
                ref={logsContainerRef}
                className="bg-black/90 text-white p-4 rounded-lg font-mono text-xs h-64 overflow-y-auto"
              >
                {logs.length === 0 ? (
                  <p className="text-gray-500">Waiting for logs...</p>
                ) : (
                  logs.map((log, idx) => {
                    let timeStr = 'N/A';
                    try {
                      if (log.timestamp) {
                        const date = new Date(log.timestamp);
                        if (!isNaN(date.getTime())) {
                          timeStr = date.toLocaleTimeString();
                        }
                      }
                    } catch (e) {
                      // Keep 'N/A'
                    }
                    
                    return (
                      <div key={idx} className="mb-1">
                        <span className="text-gray-500">
                          [{timeStr}]
                        </span>
                        {" "}
                        <span className={getLogColor(log.level)}>
                          [{log.level}]
                        </span>
                        {" "}
                        <span>{log.message}</span>
                      </div>
                    );
                  })
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Info Card */}
      <Card className="bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-950/20 dark:to-purple-950/20 border-2">
        <CardHeader>
          <CardTitle className="text-lg">About RL Trading Agents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            • <strong>PPO (Proximal Policy Optimization):</strong> On-policy algorithm with clipped surrogate objective, stable policy updates
          </p>
          <p>
            • <strong>SAC (Soft Actor-Critic):</strong> Off-policy algorithm with maximum entropy, excellent exploration-exploitation balance
          </p>
          <p>
            • <strong>Stochastic Mode:</strong> Samples from action probability distribution for more diverse trading strategies
          </p>
          <p>
            • <strong>Deterministic Mode:</strong> Always chooses highest probability action for consistent behavior
          </p>
          <p className="text-xs mt-4">
            ⚠️ <strong>Disclaimer:</strong> This is experimental AI. Results are for research purposes only and should not be used as sole basis for investment decisions.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default RLAgentsInference;
