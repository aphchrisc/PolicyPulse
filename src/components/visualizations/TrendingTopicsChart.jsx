import React, { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Typography, Box, ButtonGroup, Button } from "@mui/material";

/**
 * TrendingTopicsChart - An interactive visualization of trending legislative topics
 *
 * @param {Object} props Component props
 * @param {Array} props.data Array of topic objects with name and count properties
 * @param {number} props.limit Maximum number of topics to display
 */
const TrendingTopicsChart = ({ data = [], limit = 5 }) => {
  const [sortMode, setSortMode] = useState("count"); // 'count' or 'alphabetical'
  const [chartType, setChartType] = useState("horizontal"); // 'horizontal' or 'vertical'

  // Colors for the bars
  const colors = [
    "#2196F3",
    "#4CAF50",
    "#FF9800",
    "#E91E63",
    "#9C27B0",
    "#3F51B5",
    "#00BCD4",
    "#FFC107",
    "#FF5722",
    "#795548",
  ];

  // Process and sort the data
  const processData = () => {
    if (!data || data.length === 0) return [];

    const sortedData = [...data]
      .sort((a, b) => {
        if (sortMode === "count") {
          return b.count - a.count;
        } else {
          return a.name.localeCompare(b.name);
        }
      })
      .slice(0, limit);

    return sortedData;
  };

  const chartData = processData();

  return (
    <Box sx={{ width: "100%", height: "100%" }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Typography variant="h6">Trending Legislative Topics</Typography>
        <Box>
          <ButtonGroup size="small" aria-label="chart controls">
            <Button
              variant={sortMode === "count" ? "contained" : "outlined"}
              onClick={() => setSortMode("count")}
            >
              By Frequency
            </Button>
            <Button
              variant={sortMode === "alphabetical" ? "contained" : "outlined"}
              onClick={() => setSortMode("alphabetical")}
            >
              By Name
            </Button>
            <Button
              variant={chartType === "horizontal" ? "contained" : "outlined"}
              onClick={() => setChartType("horizontal")}
            >
              Horizontal
            </Button>
            <Button
              variant={chartType === "vertical" ? "contained" : "outlined"}
              onClick={() => setChartType("vertical")}
            >
              Vertical
            </Button>
          </ButtonGroup>
        </Box>
      </Box>

      <Box sx={{ width: "100%", height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === "horizontal" ? (
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 10, right: 30, left: 100, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="name" width={80} />
              <Tooltip
                formatter={(value, name) => [`${value} bills`, "Count"]}
                labelFormatter={(value) => `Topic: ${value}`}
              />
              <Legend />
              <Bar dataKey="count" name="Number of Bills">
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={colors[index % colors.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          ) : (
            <BarChart
              data={chartData}
              margin={{ top: 10, right: 30, left: 20, bottom: 70 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="name"
                angle={-45}
                textAnchor="end"
                height={70}
                interval={0}
              />
              <YAxis />
              <Tooltip
                formatter={(value, name) => [`${value} bills`, "Count"]}
                labelFormatter={(value) => `Topic: ${value}`}
              />
              <Legend />
              <Bar dataKey="count" name="Number of Bills">
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={colors[index % colors.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </Box>
    </Box>
  );
};

export default TrendingTopicsChart;
