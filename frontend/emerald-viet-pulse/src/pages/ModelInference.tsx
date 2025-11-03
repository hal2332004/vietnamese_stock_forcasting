import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Brain, Calendar, Activity, Sparkles } from "lucide-react";

const ModelInference = () => {
  const [selectedDate, setSelectedDate] = useState("");
  const [result, setResult] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);

  const handlePredict = async () => {
    if (!selectedDate) {
      setResult("Vui lòng chọn ngày để dự đoán");
      return;
    }
    
    setIsLoading(true);
    setResult("");
    
    // Simulate API call
    setTimeout(() => {
      setResult(`Kết quả dự đoán cho ngày ${new Date(selectedDate).toLocaleDateString('vi-VN')}:\n\nĐây là nơi hiển thị kết quả từ model AI...`);
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
            Dự đoán xu hướng thị trường bằng AI
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section - Select Time */}
        <Card className="border-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-primary" />
              Chọn Thời Gian
            </CardTitle>
            <CardDescription>
              Chọn ngày để thực hiện dự đoán
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-3">
              <Label htmlFor="date" className="text-base font-medium">
                Ngày dự đoán
              </Label>
              <Input
                id="date"
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-full h-12 text-base"
              />
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
                  Đang phân tích...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Chạy Dự Đoán
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results Section - Display Results */}
        <Card className="border-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              Kết Quả Dự Đoán
            </CardTitle>
            <CardDescription>
              Kết quả phân tích từ AI model
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!result && !isLoading ? (
              <div className="flex flex-col items-center justify-center h-[300px] border-2 border-dashed border-border rounded-lg bg-muted/10">
                <Brain className="w-16 h-16 text-muted-foreground mb-4" />
                <p className="text-muted-foreground text-center">
                  Chọn thời gian và chạy dự đoán<br />để xem kết quả
                </p>
              </div>
            ) : isLoading ? (
              <div className="flex flex-col items-center justify-center h-[300px] border-2 border-dashed border-border rounded-lg bg-primary/5">
                <Activity className="w-16 h-16 text-primary animate-spin mb-4" />
                <p className="text-foreground font-medium">Đang phân tích dữ liệu...</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Vui lòng chờ trong giây lát
                </p>
              </div>
            ) : (
              <div className="min-h-[300px] p-6 border-2 border-border rounded-lg bg-gradient-to-br from-background to-muted/20">
                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-foreground">
                    {result}
                  </pre>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Info Card */}
      <Card className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20 border-2">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Brain className="w-5 h-5" />
            Thông Tin
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            • <strong>Model AI:</strong> Sử dụng mô hình học máy để dự đoán xu hướng thị trường
          </p>
          <p>
            • <strong>Dữ liệu:</strong> Phân tích dựa trên dữ liệu lịch sử và các chỉ số kỹ thuật
          </p>
          <p>
            • <strong>Lưu ý:</strong> Kết quả chỉ mang tính tham khảo, không phải lời khuyên đầu tư
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ModelInference;
