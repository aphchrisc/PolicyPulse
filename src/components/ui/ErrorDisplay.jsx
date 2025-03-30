import React from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  Paper,
  Alert,
  AlertTitle,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";

/**
 * ErrorDisplay - A component for displaying error states with retry functionality
 *
 * @param {Object} props Component props
 * @param {string|Error} props.error The error message or object
 * @param {Function} props.onRetry Callback function to retry the failed operation
 * @param {string} props.title Title for the error display
 * @param {boolean} props.fullPage Whether to display as a full page error
 * @param {Object} props.sx Additional styles for the container
 * @param {React.ReactNode} props.children Content to display below the error
 */
const ErrorDisplay = ({
  error,
  onRetry,
  title = "Error Loading Data",
  fullPage = false,
  sx = {},
  children,
}) => {
  const errorMessage = error instanceof Error ? error.message : error;

  const getErrorContent = () => (
    <>
      <Alert severity="error" sx={{ mb: 2, width: "100%" }}>
        <AlertTitle>{title}</AlertTitle>
        {errorMessage || "An unexpected error occurred. Please try again."}
      </Alert>

      {onRetry && (
        <Button
          variant="outlined"
          color="primary"
          startIcon={<RefreshIcon />}
          onClick={onRetry}
          sx={{ mt: 1 }}
        >
          Retry
        </Button>
      )}

      {children}
    </>
  );

  if (fullPage) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          height: "80vh",
          width: "100%",
          p: 3,
          ...sx,
        }}
      >
        {getErrorContent()}
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        width: "100%",
        p: 2,
        ...sx,
      }}
    >
      {getErrorContent()}
    </Box>
  );
};

// Define prop types for ErrorDisplay
ErrorDisplay.propTypes = {
  error: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.instanceOf(Error),
    PropTypes.object,
  ]),
  onRetry: PropTypes.func,
  title: PropTypes.string,
  fullPage: PropTypes.bool,
  sx: PropTypes.object,
  children: PropTypes.node,
};

// Default props
ErrorDisplay.defaultProps = {
  title: "Error Loading Data",
  fullPage: false,
  sx: {},
};

/**
 * ErrorCard - A card wrapper with error display built in
 *
 * @param {Object} props Component props
 * @param {string|Error} props.error The error message or object
 * @param {Function} props.onRetry Callback function to retry the failed operation
 * @param {string} props.title Title for the error card
 * @param {Object} props.cardProps Additional props for the Paper component
 */
export const ErrorCard = ({ error, onRetry, title, cardProps = {} }) => {
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
      <ErrorDisplay error={error} onRetry={onRetry} title={title} />
    </Paper>
  );
};

// Define prop types for ErrorCard
ErrorCard.propTypes = {
  error: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.instanceOf(Error),
    PropTypes.object,
  ]),
  onRetry: PropTypes.func,
  title: PropTypes.string,
  cardProps: PropTypes.object,
};

// Default props
ErrorCard.defaultProps = {
  cardProps: {},
};

export default ErrorDisplay;
