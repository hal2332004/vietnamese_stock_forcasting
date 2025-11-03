import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card } from "@/components/ui/card";

interface StockDataTableProps {
  data: Array<{
    ticker: string;
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
}

export const StockDataTable = ({ data }: StockDataTableProps) => {
  return (
    <Card className="p-6 bg-card/60 backdrop-blur-sm border-border">
      <h3 className="text-lg font-semibold mb-4">Dữ liệu Cổ phiếu Chi tiết</h3>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-bold">Mã CP</TableHead>
              <TableHead className="font-bold">Ngày</TableHead>
              <TableHead className="font-bold text-right">Mở cửa</TableHead>
              <TableHead className="font-bold text-right">Cao nhất</TableHead>
              <TableHead className="font-bold text-right">Thấp nhất</TableHead>
              <TableHead className="font-bold text-right">Đóng cửa</TableHead>
              <TableHead className="font-bold text-right">Khối lượng</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((row, index) => (
              <TableRow key={index}>
                <TableCell className="font-semibold text-primary">{row.ticker}</TableCell>
                <TableCell>{new Date(row.time).toLocaleDateString("vi-VN")}</TableCell>
                <TableCell className="text-right font-medium">{row.open.toFixed(2)}</TableCell>
                <TableCell className="text-right font-medium text-positive">{row.high.toFixed(2)}</TableCell>
                <TableCell className="text-right font-medium text-negative">{row.low.toFixed(2)}</TableCell>
                <TableCell className="text-right font-medium">{row.close.toFixed(2)}</TableCell>
                <TableCell className="text-right font-medium">{row.volume.toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
};
