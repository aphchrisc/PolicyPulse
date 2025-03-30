import React, { useState } from "react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Typography,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  FormGroup,
  FormControlLabel,
  Switch,
} from "@mui/material";

/**
 * ImpactByCategory - An interactive radar chart showing impact levels across categories
 *
 * @param {Object} props Component props
 * @param {Array} props.data Array of category data with impact values
 */
const ImpactByCategory = ({ data = [] }) => {
  const [selectedMetric, setSelectedMetric] = useState("all");
  const [scaleMax, setScaleMax] = useState(100);
  const [showGrid, setShowGrid] = useState(true);

  // Generate sample data if none provided
  const defaultData = [
    { category: "Healthcare", high: 85, medium: 65, low: 45 },
    { category: "Education", high: 75, medium: 60, low: 30 },
    { category: "Environment", high: 90, medium: 70, low: 40 },
    { category: "Transportation", high: 65, medium: 50, low: 25 },
    { category: "Public Safety", high: 80, medium: 55, low: 35 },
    { category: "Economic Development", high: 70, medium: 50, low: 20 },
  ];

  const chartData = data.length > 0 ? data : defaultData;

  // Process data based on selected metric
  const processData = () => {
    if (selectedMetric === "all") {
      return chartData.map((item) => ({
        category: item.category,
        "High Impact": item.high,
        "Medium Impact": item.medium,
        "Low Impact": item.low,
      }));
    } else {
      return chartData.map((item) => ({
        category: item.category,
        [selectedMetric === "high"
          ? "High Impact"
          : selectedMetric === "medium"
          ? "Medium Impact"
          : "Low Impact"]: item[selectedMetric],
      }));
    }
  };

  const processedData = processData();

  // Return colors based on impact type
  const getColorsByType = () => {
    if (selectedMetric === "all") {
      return {
        "High Impact": "#FF5252",
        "Medium Impact": "#FFB74D",
        "Low Impact": "#4CAF50",
      };
    } else if (selectedMetric === "high") {
      return { "High Impact": "#FF5252" };
    } else if (selectedMetric === "medium") {
      return { "Medium Impact": "#FFB74D" };
    } else {
      return { "Low Impact": "#4CAF50" };
    }
  };

  const colors = getColorsByType();

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
        <Typography variant="h6">Impact Analysis by Category</Typography>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel id="impact-metric-label">Impact Metric</InputLabel>
          <Select
            labelId="impact-metric-label"
            id="impact-metric"
            value={selectedMetric}
            label="Impact Metric"
            onChange={(e) => setSelectedMetric(e.target.value)}
          >
            <MenuItem value="all">All Impacts</MenuItem>
            <MenuItem value="high">High Impact</MenuItem>
            <MenuItem value="medium">Medium Impact</MenuItem>
            <MenuItem value="low">Low Impact</MenuItem>
          </Select>
        </FormControl>

        <FormControl sx={{ width: 200 }}>
          <Typography id="scale-slider-label" gutterBottom>
            Scale Max: {scaleMax}
          </Typography>
          <Slider
            value={scaleMax}
            onChange={(e, newValue) => setScaleMax(newValue)}
            aria-labelledby="scale-slider-label"
            valueLabelDisplay="auto"
            min={50}
            max={200}
          />
        </FormControl>

        <FormGroup>
          <FormControlLabel
            control={
              <Switch
                checked={showGrid}
                onChange={(e) => setShowGrid(e.target.checked)}
              />
            }
            label="Show Grid"
          />
        </FormGroup>
      </Box>

      <Box sx={{ width: "100%", height: 400 }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart outerRadius="80%" data={processedData}>
            {showGrid && <PolarGrid />}
            <PolarAngleAxis dataKey="category" />
            <PolarRadiusAxis domain={[0, scaleMax]} />

            {Object.keys(colors).map((key) => (
              <Radar
                key={key}
                name={key}
                dataKey={key}
                stroke={colors[key]}
                fill={colors[key]}
                fillOpacity={0.6}
              />
            ))}

            <Tooltip formatter={(value) => [`${value}%`, "Impact Level"]} />
            <Legend />
          </RadarChart>
        </ResponsiveContainer>
      </Box>
    </Box>
  );
};

export default ImpactByCategory;
