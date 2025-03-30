import React from "react";
import { Box, CircularProgress, Typography, Paper } from "@mui/material";

/**
 * LoadingOverlay - A reusable component for displaying loading states
 *
 * @param {Object} props Component props
 * @param {boolean} props.isLoading Whether content is currently loading
 * @param {string} props.message Custom loading message
 * @param {React.ReactNode} props.children Content to display when not loading
 * @param {string} props.height Height of the loading container
 * @param {Object} props.containerProps Additional props for the container
 */
const LoadingOverlay = ({
  isLoading,
  message = "Loading...",
  children,
  height = "400px",
  containerProps = {},
}) => {
  if (isLoading) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          height,
          width: "100%",
          ...containerProps,
        }}
      >
        <CircularProgress size={40} />
        <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
          {message}
        </Typography>
      </Box>
    );
  }

  return children;
};

/**
 * LoadingCard - A card wrapper with loading state built in
 *
 * @param {Object} props Component props
 * @param {boolean} props.isLoading Whether content is currently loading
 * @param {string} props.message Custom loading message
 * @param {React.ReactNode} props.children Content to display when not loading
 * @param {string} props.height Height of the loading container
 * @param {Object} props.cardProps Additional props for the Paper component
 */
export const LoadingCard = ({
  isLoading,
  message,
  children,
  height,
  cardProps = {},
}) => {
  return (
    <Paper
      elevation={2}
      sx={{
        height: "auto",
        overflow: "hidden",
        borderRadius: 2,
        ...cardProps,
      }}
    >
      <LoadingOverlay isLoading={isLoading} message={message} height={height}>
        {children}
      </LoadingOverlay>
    </Paper>
  );
};

export default LoadingOverlay;
