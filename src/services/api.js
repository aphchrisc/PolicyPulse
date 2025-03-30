import axios from "axios";
import logger from "../utils/logger";

// Force the API URL to use the /api prefix for all requests
// This ensures we go through the Vite proxy which will handle
// the redirection from /bills to /legislation
const API_URL = "/api";

// Environment configuration
const ENV = import.meta.env.VITE_ENV || "development";
// Always disable mock fallback
const ENABLE_MOCK_FALLBACK = false;

// Log API URL configuration with more detailed information
logger.info("API configuration", {
  env: import.meta.env,
  apiUrl: API_URL,
});

logger.info("Using fixed API URL to ensure proxy usage", { url: API_URL });

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  // Add timeout to prevent hanging requests
  timeout: 10000,
  // Prevent axios from throwing errors on non-2xx responses
  validateStatus: (status) => status < 500,
});

// Ensure all API paths have consistent formatting and always start with '/'
const formatApiPath = (path) => {
  if (!path) return "/";
  // Ensure path starts with slash
  const formattedPath = path.startsWith("/") ? path : `/${path}`;
  // Ensure path does not have duplicate slashes
  return formattedPath.replace(/\/+/g, "/");
};

// Helper function to log API requests with standardized format
const logApiRequest = (method, url, params = {}) => {
  logger.debug(`API ${method.toUpperCase()} Request to ${url}`, { params });
};

// Add request/response interceptors for better debugging
api.interceptors.request.use(
  (config) => {
    // Only log in development environment to avoid exposing sensitive data
    if (!import.meta.env.PROD) {
      logger.debug(
        `API Request: ${config.method.toUpperCase()} ${config.url}`,
        {
          params: config.params,
          headers: config.headers,
          data: config.data,
        }
      );
    }
    return config;
  },
  (error) => {
    logger.error("API Request Error", error);
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    // Only log in development environment
    if (!import.meta.env.PROD) {
      logger.debug(`API Response: ${response.status} ${response.config.url}`, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        data: response.data,
      });
    }

    // Handle non-2xx status codes that we didn't reject in validateStatus
    if (response.status >= 400 && response.status < 500) {
      logger.warning(
        `API Client Error: ${response.status} ${response.config.url}`,
        {
          status: response.status,
          data: response.data,
          method: response.config.method,
        }
      );
    }

    return response;
  },
  (error) => {
    // Handle axios errors like network errors, timeouts, etc.
    if (error.response) {
      // The request was made and the server responded with an error status code
      logger.error("API Response Error", {
        status: error.response.status,
        data: error.response.data,
        url: error.config?.url,
        method: error.config?.method,
      });
    } else if (error.request) {
      // The request was made but no response was received
      logger.error("API No Response Error", {
        request: error.request,
        url: error.config?.url,
        method: error.config?.method,
      });
    } else {
      // Something happened in setting up the request that triggered an Error
      logger.error("API Configuration Error", {
        message: error.message,
        url: error.config?.url,
        method: error.config?.method,
      });
    }

    return Promise.reject(error);
  }
);

// Mock data for testing when API fails
const mockData = {
  impactSummary: {
    high_impact: 15,
    medium_impact: 25,
    low_impact: 10,
    total_bills: 50,
    impacted_areas: {
      Healthcare: 20,
      Education: 15,
      Environment: 10,
      Transportation: 5,
    },
  },
  recentActivity: [
    {
      id: 1,
      bill_id: "HB123",
      bill_number: "HB 123",
      title: "Healthcare Reform Act",
      description:
        "A bill to reform healthcare services and expand coverage for underserved communities",
      updated_at: "2025-03-10T14:30:00Z",
      status: "In Committee",
      jurisdiction: "U.S. Congress",
      sponsor: "Rep. Jane Smith",
      subjects: ["Healthcare", "Social Services"],
      last_action_date: "2025-03-10T14:30:00Z",
      introduced_date: "2025-02-15T10:00:00Z",
    },
    {
      id: 2,
      bill_id: "SB456",
      bill_number: "SB 456",
      title: "Education Funding Bill",
      description:
        "A bill to increase education funding for public schools and universities",
      updated_at: "2025-03-08T09:15:00Z",
      status: "Passed",
      jurisdiction: "California",
      sponsor: "Sen. John Doe",
      subjects: ["Education", "Budget"],
      last_action_date: "2025-03-08T09:15:00Z",
      introduced_date: "2025-01-20T11:30:00Z",
    },
    {
      id: 3,
      bill_id: "HB789",
      bill_number: "HB 789",
      title: "Environmental Protection Act",
      description:
        "A bill to protect natural resources and reduce carbon emissions",
      updated_at: "2025-03-05T16:45:00Z",
      status: "Introduced",
      jurisdiction: "Texas",
      sponsor: "Rep. Maria Garcia",
      subjects: ["Environment", "Energy"],
      last_action_date: "2025-03-05T16:45:00Z",
      introduced_date: "2025-03-01T08:45:00Z",
    },
    {
      id: 4,
      bill_id: "SB101",
      bill_number: "SB 101",
      title: "Mental Health Services Expansion",
      description:
        "A bill to expand mental health services and support for rural communities",
      updated_at: "2025-03-03T11:20:00Z",
      status: "In Committee",
      jurisdiction: "New York",
      sponsor: "Sen. Robert Johnson",
      subjects: ["Healthcare", "Mental Health"],
      last_action_date: "2025-03-03T11:20:00Z",
      introduced_date: "2025-02-10T14:15:00Z",
    },
    {
      id: 5,
      bill_id: "HB555",
      bill_number: "HB 555",
      title: "Infrastructure Investment and Jobs",
      description:
        "A bill to fund infrastructure projects and create jobs in construction and engineering",
      updated_at: "2025-03-01T13:10:00Z",
      status: "Passed Committee",
      jurisdiction: "U.S. Congress",
      sponsor: "Rep. David Wilson",
      subjects: ["Infrastructure", "Economic Development", "Employment"],
      last_action_date: "2025-03-01T13:10:00Z",
      introduced_date: "2025-01-15T09:30:00Z",
    },
    {
      id: 6,
      bill_id: "SB222",
      bill_number: "SB 222",
      title: "Renewable Energy Development",
      description:
        "A bill to promote renewable energy development and incentives for clean energy",
      updated_at: "2025-02-28T10:45:00Z",
      status: "Floor Vote Scheduled",
      jurisdiction: "California",
      sponsor: "Sen. Elizabeth Taylor",
      subjects: ["Energy", "Environment", "Economic Development"],
      last_action_date: "2025-02-28T10:45:00Z",
      introduced_date: "2025-01-05T15:30:00Z",
    },
    {
      id: 7,
      bill_id: "HB333",
      bill_number: "HB 333",
      title: "Digital Privacy Protection Act",
      description:
        "A bill to enhance consumer privacy protections for digital data and online services",
      updated_at: "2025-02-25T14:20:00Z",
      status: "Introduced",
      jurisdiction: "U.S. Congress",
      sponsor: "Rep. Michael Brown",
      subjects: ["Technology", "Consumer Protection", "Privacy"],
      last_action_date: "2025-02-25T14:20:00Z",
      introduced_date: "2025-02-25T14:20:00Z",
    },
    {
      id: 8,
      bill_id: "SB789",
      bill_number: "SB 789",
      title: "Affordable Housing Initiative",
      description:
        "A bill to increase funding for affordable housing development and rental assistance",
      updated_at: "2025-02-22T11:05:00Z",
      status: "In Committee",
      jurisdiction: "New York",
      sponsor: "Sen. Patricia Adams",
      subjects: ["Housing", "Urban Development", "Social Services"],
      last_action_date: "2025-02-22T11:05:00Z",
      introduced_date: "2025-01-30T13:45:00Z",
    },
    {
      id: 9,
      bill_id: "HB444",
      bill_number: "HB 444",
      title: "Small Business Support Act",
      description:
        "A bill to provide tax incentives and grants for small businesses and entrepreneurs",
      updated_at: "2025-02-18T09:30:00Z",
      status: "Passed Committee",
      jurisdiction: "Texas",
      sponsor: "Rep. Thomas Lee",
      subjects: ["Business", "Economic Development", "Taxation"],
      last_action_date: "2025-02-18T09:30:00Z",
      introduced_date: "2025-01-10T10:15:00Z",
    },
    {
      id: 10,
      bill_id: "SB567",
      bill_number: "SB 567",
      title: "Cybersecurity Enhancement Act",
      description:
        "A bill to strengthen cybersecurity standards and protect critical infrastructure",
      updated_at: "2025-02-15T15:40:00Z",
      status: "Floor Vote Scheduled",
      jurisdiction: "U.S. Congress",
      sponsor: "Sen. William Clark",
      subjects: ["Technology", "National Security", "Infrastructure"],
      last_action_date: "2025-02-15T15:40:00Z",
      introduced_date: "2025-01-05T08:30:00Z",
    },
    {
      id: 11,
      bill_id: "HB678",
      bill_number: "HB 678",
      title: "Public Transportation Funding",
      description:
        "A bill to increase funding for public transportation and reduce transit costs",
      updated_at: "2025-02-12T12:15:00Z",
      status: "Introduced",
      jurisdiction: "California",
      sponsor: "Rep. Sarah Martinez",
      subjects: ["Transportation", "Urban Development", "Environment"],
      last_action_date: "2025-02-12T12:15:00Z",
      introduced_date: "2025-02-12T12:15:00Z",
    },
    {
      id: 12,
      bill_id: "SB345",
      bill_number: "SB 345",
      title: "Water Conservation Act",
      description:
        "A bill to promote water conservation practices and protect water resources",
      updated_at: "2025-02-08T10:50:00Z",
      status: "In Committee",
      jurisdiction: "Texas",
      sponsor: "Sen. Christopher Rodriguez",
      subjects: ["Environment", "Agriculture", "Natural Resources"],
      last_action_date: "2025-02-08T10:50:00Z",
      introduced_date: "2025-01-25T14:00:00Z",
    },
  ],
  statusBreakdown: {
    introduced: 15,
    in_committee: 8,
    passed_committee: 5,
    floor_vote: 3,
    passed: 2,
    enacted: 1,
    vetoed: 0,
  },
  trendingTopics: [
    { term: "healthcare", count: 20 },
    { term: "education", count: 15 },
    { term: "infrastructure", count: 10 },
    { term: "energy", count: 8 },
    { term: "economy", count: 5 },
  ],
};

// Log environment configuration
logger.info("API environment configuration", {
  env: ENV,
  enableMockFallback: ENABLE_MOCK_FALLBACK,
  apiUrl: API_URL,
});

// Helper function to handle API errors with configurable fallback
const handleApiError = (error, errorMessage, mockData, params = {}) => {
  logger.error(errorMessage, { error, params });

  // Never use mock data, always throw the original error
  throw error;
};

// Legislation API endpoints
export const getLegislation = async (params = {}) => {
  try {
    // Prepare params, ensuring sorting is specified
    const apiParams = {
      ...params,
      // Default to sorting by updated_at desc if not specified
      sort_by: params.sort_by || "updated_at",
      sort_direction: params.sort_direction || "desc",
    };

    // Log the request for debugging
    logger.debug("Fetching legislation with params:", apiParams);

    const response = await api.get("/legislation/", { params: apiParams });
    logger.debug("Legislation API response:", {
      status: response.status,
      data: response.data,
    });

    return response;
  } catch (error) {
    logger.error("Error fetching legislation", { error, params });
    throw error;
  }
};

export const getLegislationById = async (id) => {
  try {
    const endpoint = formatApiPath(`/legislation/${id}/`);
    logApiRequest("GET", endpoint, { id });

    // Added timeout extension for potentially larger responses
    const response = await api.get(endpoint, {
      timeout: 15000, // Increase timeout for detail requests which might be larger
    });

    // Validate the response
    if (response.status !== 200) {
      logger.error(`Error fetching legislation by ID ${id}:`, {
        status: response.status,
        statusText: response.statusText,
        data: response.data,
      });

      // Throw custom error with more details
      const errorMessage =
        response.data?.message || response.statusText || "Unknown error";
      throw new Error(`Failed to fetch legislation: ${errorMessage}`);
    }

    // Additional validation of response data
    if (!response.data) {
      logger.error(`Empty response for legislation ID ${id}`);
      throw new Error("No data received from the server");
    }

    // Handle the case where response.data is a string (raw JSON)
    if (typeof response.data === "string") {
      try {
        logger.debug(`Parsing string response for legislation ${id}`);
        const parsedData = JSON.parse(response.data);
        response.data = parsedData;
      } catch (parseError) {
        logger.error(`Failed to parse legislation data for ID ${id}:`, {
          error: parseError.message,
          data: response.data.substring(0, 200) + "...", // Log first 200 chars
        });
        // Continue with the string response, components will handle it
      }
    }

    // Log successful response for debugging
    logger.debug(`Successfully retrieved legislation ${id}`);

    // Transform any inconsistent field names if necessary
    let data = response.data;

    // Ensure data is an object
    if (typeof data !== "object" || data === null) {
      logger.warn(`Unexpected data type for legislation ${id}:`, {
        type: typeof data,
        isNull: data === null,
      });

      // Use minimal data structure as fallback
      data = {
        id: parseInt(id),
        bill_number: `Bill #${id}`,
        title: `Bill ${id}`,
        description: "Details unavailable in expected format",
        jurisdiction: "Unknown",
        bill_status: "Unknown",
      };
    }

    // If jurisdiction is missing but govt_source is present, use that
    if (!data.jurisdiction && data.govt_source) {
      data.jurisdiction = data.govt_source;
    } else if (!data.jurisdiction && data.state) {
      data.jurisdiction = data.state;
    }

    // If status field naming is inconsistent
    if (!data.bill_status && data.status) {
      data.bill_status = data.status;
    }

    // Format dates consistently
    const dateFields = [
      "bill_introduced_date",
      "bill_last_action_date",
      "bill_status_date",
      "last_api_check",
      "created_at",
      "updated_at",
      "last_updated",
    ];

    dateFields.forEach((field) => {
      if (data[field] && typeof data[field] === "string") {
        // Ensure date is in ISO format
        if (!data[field].includes("T")) {
          try {
            const date = new Date(data[field]);
            data[field] = date.toISOString();
          } catch (e) {
            // Keep original if parsing fails
          }
        }
      }
    });

    // Handle last_updated field
    if (!data.last_updated && data.updated_at) {
      data.last_updated = data.updated_at;
    } else if (!data.last_updated && !data.updated_at) {
      // Fallback to current time
      data.last_updated = new Date().toISOString();
      data.updated_at = data.last_updated;
    }

    // Ensure sponsors are always an array
    if (!data.sponsors) {
      data.sponsors = [];
    } else if (!Array.isArray(data.sponsors)) {
      data.sponsors = [data.sponsors];
    }

    // Ensure required nested objects exist
    const requiredObjects = ["latest_text", "analysis", "priority"];
    requiredObjects.forEach((field) => {
      if (!data[field]) {
        data[field] = {};
      }
    });

    // Add the transformed data back to the response
    response.data = data;

    return response;
  } catch (error) {
    // Handle ConnectionError or NetworkError
    if (
      error.name === "Error" &&
      (error.message.includes("Network Error") ||
        error.message.includes("Connection") ||
        error.message.includes("ECONNREFUSED"))
    ) {
      logger.error(`Network error fetching legislation ${id}:`, {
        error: error.message,
      });
      throw new Error(
        `Network error: Unable to connect to API server. Please check your connection and try again.`
      );
    }

    // Handle ResponseValidationError specifically
    if (error.message && error.message.includes("ResponseValidationError")) {
      try {
        // Try again with a ?raw=true parameter to bypass response validation
        logger.debug(
          `Attempting to fetch legislation ${id} with raw parameter to bypass validation`
        );
        const rawResponse = await api.get(`/legislation/${id}/?raw=true`, {
          timeout: 15000,
        });

        if (rawResponse.status === 200) {
          logger.debug(`Successfully retrieved raw legislation data for ${id}`);

          let data = rawResponse.data;

          // Handle case where response is a string
          if (typeof data === "string") {
            try {
              data = JSON.parse(data);
            } catch (parseError) {
              logger.error(
                `Failed to parse raw legislation data for ID ${id}:`,
                {
                  error: parseError.message,
                }
              );
              // Continue with the string
            }
          }

          // Normalize the data
          // Ensure all required fields are present
          const normalizedData = {
            id: parseInt(id),
            external_id: data.external_id || `unknown_${id}`,
            bill_number: data.bill_number || `#${id}`,
            title: data.title || "Untitled Bill",
            description: data.description || "",
            jurisdiction: data.jurisdiction || data.govt_source || "Unknown",
            bill_status: data.bill_status || data.status || "Unknown",
            updated_at: data.updated_at || new Date().toISOString(),
            last_updated:
              data.last_updated || data.updated_at || new Date().toISOString(),
            sponsors: Array.isArray(data.sponsors)
              ? data.sponsors
              : data.sponsor
              ? [{ name: data.sponsor }]
              : [],
            latest_text: data.latest_text || { text: "No text available" },
            analysis: data.analysis || {},
            ...data,
          };

          return { data: normalizedData, status: 200 };
        }
      } catch (rawError) {
        logger.error(`Failed to fetch raw legislation data for ${id}:`, {
          error: rawError.message,
        });
      }

      // If all else fails, create a minimal valid bill object
      const minimalBill = {
        id: parseInt(id),
        external_id: `bill_${id}`,
        bill_number: `#${id}`,
        title: `Bill #${id}`,
        description: "Details currently unavailable",
        jurisdiction: "Unknown",
        bill_status: "Unknown",
        updated_at: new Date().toISOString(),
        last_updated: new Date().toISOString(),
        sponsors: [],
        latest_text: { text: "Bill text unavailable" },
        analysis: {},
      };

      logger.warn(`Using minimal bill data for ${id} due to validation errors`);
      return { data: minimalBill, status: 200 };
    }

    logger.error(`Error fetching legislation by ID ${id}:`, {
      error: error.message,
      stack: error.stack,
      name: error.name,
    });

    // Provide a more user-friendly error
    const userFriendlyError = new Error(
      error.message.includes("ResponseValidationError")
        ? "The server returned data in an unexpected format. Please try again later or contact support."
        : `Unable to load bill details: ${error.message}`
    );

    // Preserve original error properties
    userFriendlyError.originalError = error;
    userFriendlyError.status = error.response?.status;

    // Re-throw the user-friendly error
    throw userFriendlyError;
  }
};

export const searchLegislation = async (params = {}) => {
  try {
    // Check if using advanced search based on filters property
    const isAdvancedSearch =
      typeof params === "object" &&
      params.filters &&
      Object.keys(params.filters).length > 0;

    // Prepare request parameters
    let requestParams = { ...params };

    // Handle advanced search differently
    if (isAdvancedSearch) {
      logger.debug("Performing advanced legislation search", requestParams);

      // Use POST for advanced search
      const response = await api.post("/legislation/advanced-search/", {
        filters: params.filters,
        limit: params.limit || 50,
        offset: params.offset || 0,
      });

      return response;
    } else {
      // Use GET for basic keyword search
      logger.debug("Performing basic legislation search", requestParams);

      // Remove filters if present but empty
      if (
        requestParams.filters &&
        Object.keys(requestParams.filters).length === 0
      ) {
        delete requestParams.filters;
      }

      return await api.get("/legislation/search/", { params: requestParams });
    }
  } catch (error) {
    logger.error("Error searching legislation", { error, params });
    throw error;
  }
};

// Analysis API endpoints
export const getAnalysisById = async (id) => {
  return await api.get(`/analysis/${id}/`);
};

export const getLegislationAnalysis = async (legId) => {
  return await api.get(`/legislation/${legId}/analysis/`);
};

export const getAnalysisHistory = async (legId) => {
  return await api.get(`/legislation/${legId}/analysis/history/`);
};

export const createAnalysis = async (data) => {
  return await api.post("/analysis/", data);
};

// Enhanced analysis API with retry logic
export const fetchLegislationAnalysis = async (
  legId,
  retries = 3,
  delay = 1000
) => {
  let lastError;

  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      return await getLegislationAnalysis(legId);
    } catch (error) {
      logger.warn(`Analysis fetch attempt ${attempt + 1} failed:`, error);
      lastError = error;

      // Wait before retrying
      if (attempt < retries - 1) {
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
};

// Dashboard API endpoints
export const getImpactSummary = async (
  impactType = "public_health",
  timePeriod = "current"
) => {
  try {
    const response = await api.get("/dashboard/impact-summary/", {
      params: { impact_type: impactType, time_period: timePeriod },
    });
    return response;
  } catch (error) {
    logger.error("Error fetching impact summary", {
      error,
      impactType,
      timePeriod,
    });
    throw error;
  }
};

export const getRecentActivity = async (days = 30, limit = 10) => {
  try {
    const response = await api.get("/dashboard/recent-activity/", {
      params: { days, limit },
    });
    return response;
  } catch (error) {
    logger.error("Error fetching recent activity", { error, days, limit });
    throw error;
  }
};

export const getStatusBreakdown = async () => {
  try {
    const response = await api.get("/dashboard/status-breakdown/");
    return response;
  } catch (error) {
    logger.error("Error fetching status breakdown", { error });
    throw error;
  }
};

export const getTrendingTopics = async (limit = 5) => {
  try {
    const response = await api.get("/dashboard/trending-topics/", {
      params: { limit },
    });
    return response;
  } catch (error) {
    logger.error("Error fetching trending topics", { error, limit });
    throw error;
  }
};

export const getImpactDistribution = async (impactType = "public_health") => {
  return await api.get("/dashboard/impact-distribution/", {
    params: { impact_type: impactType },
  });
};

export const getActivityTimeline = async (days = 90) => {
  return await api.get("/dashboard/activity-timeline/", {
    params: { days },
  });
};

// Search API endpoints
export const searchBills = async (query, filters = {}) => {
  // Extract pagination parameters
  const { page = 1, limit = 20, ...otherFilters } = filters;

  // Validate pagination parameters
  const validatedPage = Math.max(1, parseInt(page, 10) || 1);
  const validatedLimit = Math.min(100, Math.max(1, parseInt(limit, 10) || 20));

  return await api.get("/legislation/search", {
    params: {
      query,
      page: validatedPage,
      limit: validatedLimit,
      ...otherFilters,
    },
  });
};

// Bill service for bill-related operations
export const billService = {
  getBillById: async (billId) => {
    const response = await getLegislationById(billId);
    return response.data;
  },
  searchBills: async (params) => {
    // Use the enhanced searchBills function with pagination if query parameter is provided
    let response;
    if (params.query) {
      response = await searchBills(params.query, params);
    } else {
      response = await getLegislation(params);
    }
    return response.data;
  },
  getAnalysis: async (billId) => {
    // Try to use the enhanced fetchLegislationAnalysis with retry logic
    const response = await fetchLegislationAnalysis(billId);
    return response.data;
  },
  /**
   * Performs an advanced search for legislation using POST request.
   * @param {object} searchParams - Parameters matching the BillSearchQuery model.
   * @param {string} [searchParams.query=""] - Search query string.
   * @param {object} [searchParams.filters={}] - Filters object (e.g., { impact_level: ['high'] }).
   * @param {string} [searchParams.sort_by="relevance"] - Field to sort by.
   * @param {string} [searchParams.sort_dir="desc"] - Sort direction.
   * @param {number} [searchParams.limit=50] - Max results.
   * @param {number} [searchParams.offset=0] - Results to skip.
   * @returns {Promise<object>} - The API response data.
   */
  searchLegislationAdvanced: async (searchParams = {}) => {
    try {
      const payload = {
        query: searchParams.query || "",
        filters: searchParams.filters || {},
        sort_by: searchParams.sort_by || "relevance",
        sort_dir: searchParams.sort_dir || "desc",
        limit: searchParams.limit || 50,
        offset: searchParams.offset || 0,
      };
      logger.debug("Performing advanced legislation search via POST", payload);
      const response = await api.post("/legislation/advanced-search/", payload);
      
      // Handle potential errors even if status < 500
      if (response.status >= 400) {
          logger.error(`Advanced search failed with status ${response.status}`, { data: response.data });
          throw new Error(`Advanced search failed: ${response.data?.detail || response.statusText}`);
      }
      
      return response.data; // Should contain { count, items, page_info }
    } catch (error) {
      logger.error("Error performing advanced legislation search", { error, searchParams });
      throw error; // Re-throw after logging
    }
  },
  getDashboardData: async () => {
    // Fetch multiple dashboard data sources in parallel
    const [
      recentActivityResponse,
      impactSummaryResponse,
      statusBreakdownResponse,
      trendingTopicsResponse,
    ] = await Promise.all([
      getRecentActivity(),
      getImpactSummary(),
      getStatusBreakdown(),
      getTrendingTopics(),
    ]);

    // Return the real data from the API
    return {
      recentActivity: {
        recent_legislation: recentActivityResponse.data.items || [],
      },
      impactSummary: { categories: impactSummaryResponse.data },
      statusBreakdown: { status_counts: statusBreakdownResponse.data },
      trendingTopics: { topics: trendingTopicsResponse.data.topics || [] },
    };
  },
};

// Health check endpoint
export const healthCheck = async () => {
  try {
    logger.info("Performing API health check...");
    const response = await api.get("/health");

    // Explicitly check for non-200 status even if Axios doesn't throw
    if (response.status !== 200) {
        logger.error(`Health check failed with status: ${response.status}`, { responseData: response.data });
        throw new Error(`Health check failed with status ${response.status}`);
    }

    // Check if the response data indicates success (adjust based on actual response structure)
    if (response.data?.status !== 'ok') {
         logger.warn(`Health check response indicates non-ok status:`, { responseData: response.data });
         // Optionally throw an error here too if 'ok' status is critical
         // throw new Error(`Health check returned non-ok status: ${response.data?.status}`);
    }

    return { data: response.data };
  } catch (error) {
    // Log the error regardless of its origin (Axios error or manual throw)
    logger.error("Health check failed:", { errorMessage: error.message, errorObj: error });
    // Re-throw the error so the caller knows the check failed
    throw error;
  }
};

export default api;
