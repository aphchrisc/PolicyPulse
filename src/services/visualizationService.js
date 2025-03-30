// visualizationService.js
import * as d3 from "d3";

/**
 * Helper function to strip HTML tags and get plain text
 * @param {string} html - HTML content
 * @returns {string} - Plain text without HTML tags
 */
const stripHtml = (html) => {
  if (!html) return "";

  try {
    // Check if we're in a browser environment
    if (typeof window !== "undefined" && window.DOMParser) {
      // Create a DOM parser to handle HTML properly
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");

      // Get text content from parsed HTML
      return doc.body.textContent || doc.body.innerText || "";
    } else {
      // Fallback for non-browser environments
      throw new Error("DOMParser not available");
    }
  } catch (error) {
    // Fallback to regex for simple HTML stripping if DOMParser fails
    return html
      .replace(/<[^>]*>?/gm, " ")
      .replace(/&nbsp;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#039;/g, "'")
      .replace(/\s\s+/g, " ")
      .trim();
  }
};

/**
 * Extract meaningful terms from text content
 * @param {string} text - Text content to analyze
 * @returns {Array} - Array of term objects with text and value properties
 */
const extractTermsFromText = (text) => {
  if (!text || typeof text !== "string") return [];

  // Strip HTML if the content contains HTML tags
  const plainText = text.includes("<") ? stripHtml(text) : text;

  // Common words to exclude
  const commonWords = new Set([
    "the",
    "and",
    "a",
    "to",
    "in",
    "of",
    "for",
    "be",
    "is",
    "on",
    "that",
    "by",
    "this",
    "with",
    "as",
    "an",
    "are",
    "at",
    "or",
    "not",
    "but",
    "it",
    "its",
    "from",
    "was",
    "were",
    "will",
    "would",
    "could",
    "should",
    "have",
    "has",
    "had",
    "may",
    "can",
    "shall",
    "such",
    "must",
    "any",
    "all",
    "if",
    "which",
    "when",
    "where",
    "who",
    "whom",
    "whose",
    "what",
    "why",
    "how",
    "their",
    "they",
    "them",
    "these",
    "those",
    "there",
    "than",
    "then",
    "section",
    "act",
    "bill",
  ]);

  // Extract words (minimum 3 letters) and count frequency
  const words = plainText.toLowerCase().match(/\b[a-z]{3,}\b/g) || [];
  const wordCounts = {};

  words.forEach((word) => {
    if (!commonWords.has(word)) {
      wordCounts[word] = (wordCounts[word] || 0) + 1;
    }
  });

  // Convert to array and sort by frequency
  return Object.entries(wordCounts)
    .filter(([_, count]) => count > 1) // Only include words that appear more than once
    .sort((a, b) => b[1] - a[1])
    .slice(0, 50) // Take top 50 terms
    .map(([text, count]) => ({ text, value: count * 5 }));
};

/**
 * Prepares data for a word cloud visualization
 * @param {Object} analysisData - The analysis data from the API
 * @returns {Array} - Data formatted for react-d3-cloud
 */
export const prepareWordCloudData = (analysisData) => {
  if (!analysisData) {
    return [];
  }

  let data = [];

  // Try to extract key terms from different possible locations in the data structure

  // Check for structured key_terms data
  if (analysisData.key_terms) {
    // For array format
    if (Array.isArray(analysisData.key_terms)) {
      data = analysisData.key_terms.map((term) => {
        // Handle different property names in the API response
        const termText =
          term.term || term.text || term.word || term.key || String(term);
        const termValue =
          term.score || term.value || term.weight || term.frequency || 10;

        return {
          text: termText,
          value: typeof termValue === "number" ? termValue * 100 : 50, // Scale appropriately
        };
      });
    }
    // For object format (term -> score mapping)
    else if (typeof analysisData.key_terms === "object") {
      data = Object.entries(analysisData.key_terms).map(([term, score]) => ({
        text: term,
        value: typeof score === "number" ? score * 100 : 50,
      }));
    }
  }

  // Check for keywords field
  if (data.length === 0 && analysisData.keywords) {
    if (Array.isArray(analysisData.keywords)) {
      data = analysisData.keywords.map((keyword, index) => ({
        text: typeof keyword === "string" ? keyword : String(keyword),
        value: 100 - index * 5, // Descending values based on position
      }));
    } else if (typeof analysisData.keywords === "object") {
      data = Object.entries(analysisData.keywords).map(
        ([keyword, value], index) => ({
          text: keyword,
          value: typeof value === "number" ? value * 100 : 100 - index * 5,
        })
      );
    }
  }

  // Check for topics field
  if (data.length === 0 && analysisData.topics) {
    if (typeof analysisData.topics === "object") {
      data = Object.entries(analysisData.topics).map(([topic, value]) => ({
        text: topic,
        value: typeof value === "number" ? value * 100 : 50,
      }));
    }
  }

  // Try to extract terms from bill text directly
  if (data.length === 0) {
    // Check for bill text in various possible locations
    let textContent = null;

    if (analysisData.latest_text && analysisData.latest_text.text) {
      textContent = analysisData.latest_text.text;
    } else if (analysisData.bill_text) {
      textContent = analysisData.bill_text;
    } else if (analysisData.text_content) {
      textContent = analysisData.text_content;
    } else if (analysisData.content) {
      textContent = analysisData.content;
    } else if (analysisData.summary) {
      textContent = analysisData.summary;
    } else if (analysisData.description) {
      textContent = analysisData.description;
    }

    // If we found some text content, extract terms from it
    if (textContent) {
      data = extractTermsFromText(textContent);
    }
  }

  // If we still have no data, create a minimal set of placeholder terms
  if (data.length === 0) {
    data = [
      { text: "Legislation", value: 100 },
      { text: "Policy", value: 80 },
      { text: "Government", value: 60 },
      { text: "Regulation", value: 50 },
      { text: "Public", value: 40 },
    ];
  }

  return data;
};

/**
 * Prepares data for a timeline visualization
 * @param {Object} billData - The bill data from the API
 * @returns {Array} - Data formatted for timeline visualization
 */
export const prepareTimelineData = (billData) => {
  if (!billData || !billData.history) {
    return [];
  }

  return billData.history.map((event, index) => ({
    id: index,
    date: new Date(event.date),
    title: event.action,
    description: event.description || "",
    status: determineStatus(event.action),
    icon: determineIcon(event.action),
  }));
};

/**
 * Determines the status type for a timeline event
 * @param {string} action - The action text
 * @returns {string} - Status identifier (major, critical, success, default)
 */
const determineStatus = (action) => {
  const actionLower = action?.toLowerCase() || "";

  if (actionLower.includes("passed") || actionLower.includes("approved")) {
    return "success";
  } else if (
    actionLower.includes("introduced") ||
    actionLower.includes("filed")
  ) {
    return "major";
  } else if (actionLower.includes("vetoed") || actionLower.includes("failed")) {
    return "critical";
  } else {
    return "default";
  }
};

/**
 * Determines the appropriate icon for a timeline event
 * @param {string} action - The action text
 * @returns {string} - Icon identifier
 */
const determineIcon = (action) => {
  const actionLower = action.toLowerCase();

  if (actionLower.includes("introduced") || actionLower.includes("filed")) {
    return "new";
  } else if (actionLower.includes("committee")) {
    return "committee";
  } else if (
    actionLower.includes("passed") ||
    actionLower.includes("approved")
  ) {
    return "passed";
  } else if (actionLower.includes("signed")) {
    return "signed";
  } else if (actionLower.includes("vetoed")) {
    return "vetoed";
  } else {
    return "default";
  }
};

/**
 * Prepares data for impact assessment visualization
 * @param {Object} analysisData - The analysis data from the API
 * @returns {Array} - Data formatted for radar/spider chart
 */
export const prepareImpactData = (analysisData) => {
  if (!analysisData || !analysisData.impact_assessment) {
    return [];
  }

  // Convert impact assessment object to array format for visualization
  return Object.entries(analysisData.impact_assessment).map(
    ([category, value]) => ({
      category: formatCategoryName(category),
      value: value,
    })
  );
};

/**
 * Formats a category name for display (converts snake_case to Title Case)
 * @param {string} category - The category name in snake_case
 * @returns {string} - Formatted category name
 */
const formatCategoryName = (category) => {
  return category
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

/**
 * Prepares colors for visualization based on impact levels
 * @param {Array} data - The prepared impact data
 * @returns {Object} - Color configuration for visualizations
 */
export const getImpactColors = (data) => {
  const colorScale = d3
    .scaleLinear()
    .domain([0, 50, 100])
    .range(["#4caf50", "#ff9800", "#f44336"]);

  return {
    scale: colorScale,
    byCategory: Object.fromEntries(
      data.map((item) => [item.category, colorScale(item.value)])
    ),
  };
};

export const prepareKeyTermsData = (analysisData) => {
  // Use the enhanced prepareWordCloudData function
  return prepareWordCloudData(analysisData);
};

/**
 * Alias for prepareTimelineData for backward compatibility
 * @param {Object} billData - The bill data from the API
 * @returns {Array} - Data formatted for timeline visualization
 */
export const prepareBillTimelineData = (billData) => {
  // Use the enhanced prepareTimelineData function
  const timelineData = prepareTimelineData(billData);

  // Format dates as strings for compatibility with existing code
  return timelineData.map((item) => ({
    ...item,
    date: item.date instanceof Date ? item.date : new Date(item.date),
  }));
};

export default {
  prepareWordCloudData,
  prepareTimelineData,
  prepareImpactData,
  getImpactColors,
  prepareKeyTermsData,
  prepareBillTimelineData,
};
