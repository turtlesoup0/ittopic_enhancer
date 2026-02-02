import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { DomainStats } from '@/types/api';

interface CompletionChartProps {
  data: DomainStats[];
}

export function CompletionChart({ data }: CompletionChartProps) {
  // 정렬된 데이터
  const sortedData = useMemo(() => {
    return [...data].sort((a, b) => a.domain.localeCompare(b.domain));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={sortedData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="domain"
          angle={-45}
          textAnchor="end"
          height={100}
          fontSize={12}
        />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="total_topics" name="전체 토픽" fill="#3b82f6" />
        <Bar dataKey="completed_count" name="완성된 토픽" fill="#22c55e" />
      </BarChart>
    </ResponsiveContainer>
  );
}
