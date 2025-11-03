import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { 
  Brain, 
  Calendar, 
  Activity, 
  Sparkles, 
  TrendingUp, 
  TrendingDown,
  ArrowRight,
  Info
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface PredictionResult {
  date: string;
  trend: "up" | "down";
  percentage: number;
  confidence: number;
}

const ModelInference = () => {
  const [selectedDate, setSelectedDate] = useState("");
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handlePredict = async () => {
    if (!selectedDate) {
      return;
    }
    
    setIsLoading(true);
    setResult(null);
    
    // Simulate API call - Replace with actual API call
    setTimeout(() => {
      // Mock result - replace with real API response
      const mockResult: PredictionResult = {
        date: selectedDate,
        trend: Math.random() > 0.5 ? "up" : "down",
        percentage: Math.random() * 10 + 0.5, // Random between 0.5-10.5%
        confidence: Math.random() * 30 + 70, // Random between 70-100%
      };
      setResult(mockResult);
      setIsLoading(false);
    }, 1500);
  };

  const getNextDay = (dateString: string) => {
    const date = new Date(dateString);
    date.setDate(date.getDate() + 1);
    return date.toLocaleDateString('vi-VN', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-3">
          <div className="flex justify-center">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-600 flex items-center justify-center shadow-xl">
              <Brain className="w-10 h-10 text-white" />
            </div>
          </div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
            Model Inference AI
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Dự đoán xu hướng giá cổ phiếu ngày tiếp theo với độ chính xác cao
          </p>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Input Section */}
          <div className="lg:col-span-2">
            <Card className="border-2 shadow-xl backdrop-blur-sm bg-white/80 dark:bg-slate-900/80">
              <CardHeader className="space-y-1">
                <CardTitle className="flex items-center gap-2 text-2xl">
                  <Calendar className="w-6 h-6 text-purple-600" />
                  Chọn Ngày
                </CardTitle>
                <CardDescription className="text-base">
                  Chọn một ngày để dự đoán xu hướng ngày tiếp theo
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <Label htmlFor="date" className="text-base font-semibold text-foreground">
                    Ngày giao dịch
                  </Label>
                  <Input
                    id="date"
                    type="date"
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="w-full h-14 text-lg border-2 focus:ring-2 focus:ring-purple-500"
                  />
                  
                  {selectedDate && (
                    <div className="flex items-center gap-2 p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
                      <Info className="w-5 h-5 text-blue-600 flex-shrink-0" />
                      <div className="text-sm">
                        <p className="font-medium text-blue-900 dark:text-blue-100">
                          Ngày dự đoán:
                        </p>
                        <p className="text-blue-700 dark:text-blue-300">
                          {getNextDay(selectedDate)}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                <Button 
                  onClick={handlePredict}
                  disabled={!selectedDate || isLoading}
                  className="w-full h-14 text-lg gap-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 shadow-lg"
                  size="lg"
                >
                  {isLoading ? (
                    <>
                      <Activity className="w-6 h-6 animate-spin" />
                      Đang phân tích...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-6 h-6" />
                      Dự Đoán Xu Hướng
                      <ArrowRight className="w-5 h-5" />
                    </>
                  )}
                </Button>

                <div className="pt-4 space-y-3 border-t">
                  <p className="text-xs text-muted-foreground flex items-center gap-2">
                    <Info className="w-4 h-4" />
                    Mô hình AI phân tích 33+ chỉ số kỹ thuật
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Results Section */}
          <div className="lg:col-span-3">
            <Card className="border-2 shadow-xl backdrop-blur-sm bg-white/80 dark:bg-slate-900/80">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-2xl">
                  <Activity className="w-6 h-6 text-blue-600" />
                  Kết Quả Dự Đoán
                </CardTitle>
                <CardDescription className="text-base">
                  Xu hướng và biến động giá dự kiến
                </CardDescription>
              </CardHeader>
              <CardContent className="min-h-[400px]">
                {!result && !isLoading ? (
                  <div className="flex flex-col items-center justify-center h-full py-16 border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
                    <Brain className="w-24 h-24 text-slate-400 mb-6" />
                    <p className="text-xl font-medium text-slate-600 dark:text-slate-400 text-center">
                      Chọn ngày và nhấn "Dự Đoán"
                    </p>
                    <p className="text-sm text-slate-500 dark:text-slate-500 mt-2">
                      để xem kết quả phân tích AI
                    </p>
                  </div>
                ) : isLoading ? (
                  <div className="flex flex-col items-center justify-center h-full py-16 border-2 border-blue-200 dark:border-blue-800 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20">
                    <Activity className="w-24 h-24 text-blue-600 animate-spin mb-6" />
                    <p className="text-xl font-semibold text-blue-900 dark:text-blue-100">
                      Đang phân tích dữ liệu...
                    </p>
                    <p className="text-sm text-blue-700 dark:text-blue-300 mt-2">
                      AI đang xử lý các chỉ số kỹ thuật
                    </p>
                  </div>
                ) : result ? (
                  <div className="space-y-6 animate-in fade-in duration-500">
                    {/* Trend Display */}
                    <div className={`relative overflow-hidden rounded-2xl p-8 ${
                      result.trend === "up" 
                        ? "bg-gradient-to-br from-green-500 to-emerald-600" 
                        : "bg-gradient-to-br from-red-500 to-rose-600"
                    }`}>
                      <div className="relative z-10 text-center text-white">
                        <div className="flex justify-center mb-4">
                          {result.trend === "up" ? (
                            <div className="w-24 h-24 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                              <TrendingUp className="w-14 h-14" strokeWidth={2.5} />
                            </div>
                          ) : (
                            <div className="w-24 h-24 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                              <TrendingDown className="w-14 h-14" strokeWidth={2.5} />
                            </div>
                          )}
                        </div>
                        
                        <h3 className="text-3xl font-bold mb-2">
                          {result.trend === "up" ? "XU HƯỚNG TĂNG" : "XU HƯỚNG GIẢM"}
                        </h3>
                        
                        <div className="flex items-center justify-center gap-2 mb-4">
                          <span className="text-6xl font-black">
                            {result.trend === "up" ? "+" : "-"}{result.percentage.toFixed(2)}%
                          </span>
                        </div>
                        
                        <Badge 
                          className="bg-white/20 backdrop-blur-sm text-white border-white/30 px-4 py-1 text-base"
                        >
                          Độ tin cậy: {result.confidence.toFixed(1)}%
                        </Badge>
                      </div>
                      
                      {/* Decorative elements */}
                      <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full -mr-20 -mt-20"></div>
                      <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/10 rounded-full -ml-16 -mb-16"></div>
                    </div>

                    {/* Details */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 rounded-xl border-2 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900">
                        <p className="text-sm text-muted-foreground mb-1">Ngày dự đoán</p>
                        <p className="font-bold text-lg text-foreground">
                          {getNextDay(result.date).split(',')[0]}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(result.date).toLocaleDateString('vi-VN')} → {getNextDay(result.date).split(', ')[1]}
                        </p>
                      </div>
                      
                      <div className="p-4 rounded-xl border-2 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900">
                        <p className="text-sm text-muted-foreground mb-1">Biến động dự kiến</p>
                        <p className={`font-bold text-lg ${
                          result.trend === "up" ? "text-green-600" : "text-red-600"
                        }`}>
                          {result.trend === "up" ? "Tăng" : "Giảm"} {result.percentage.toFixed(2)}%
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          So với ngày hiện tại
                        </p>
                      </div>
                    </div>

                    {/* Info */}
                    <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
                      <div className="flex gap-3">
                        <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-amber-900 dark:text-amber-100">
                          <p className="font-semibold mb-1">Lưu ý quan trọng:</p>
                          <p className="text-amber-800 dark:text-amber-200">
                            Kết quả dự đoán chỉ mang tính tham khảo, dựa trên phân tích dữ liệu lịch sử. 
                            Không nên sử dụng làm lời khuyên đầu tư tài chính.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Info Footer */}
        <Card className="border-2 shadow-lg bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-950/20 dark:to-blue-950/20">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-600" />
              Về Model AI
            </CardTitle>
          </CardHeader>
          <CardContent className="grid md:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="font-semibold text-foreground mb-1">🎯 Độ chính xác</p>
              <p className="text-muted-foreground">
                Model được huấn luyện với hàng nghìn điểm dữ liệu lịch sử
              </p>
            </div>
            <div>
              <p className="font-semibold text-foreground mb-1">📊 Chỉ số phân tích</p>
              <p className="text-muted-foreground">
                33+ chỉ số kỹ thuật: MA, RSI, MACD, Bollinger Bands...
              </p>
            </div>
            <div>
              <p className="font-semibold text-foreground mb-1">🤖 Công nghệ AI</p>
              <p className="text-muted-foreground">
                LSTM & Transformer neural networks
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ModelInference;
