import React, { useState, useEffect, useRef } from "react";
import WordCloud from "react-d3-cloud";
import { prepareWordCloudData } from "../../services/visualizationService";
import { FiInfo } from "react-icons/fi";
import logger from "../../utils/logger";

const KeyTermsCloud = ({
  analysisData,
  height = 300,
  width = 500,
  isDarkMode = false,
}) => {
  const [wordCloudData, setWordCloudData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hoveredWord, setHoveredWord] = useState(null);
  const [error, setError] = useState(null);
  const [dimensions, setDimensions] = useState({ width, height });
  const containerRef = useRef(null);
  const renderStartTime = useRef(Date.now()).current;

  // Helper function to strip HTML tags and get plain text
  const stripHtml = (html) => {
    if (!html) return "";

    console.log("KeyTermsCloud: Extracting text from HTML", {
      htmlLength: html?.length || 0,
    });

    try {
      if (typeof window !== "undefined" && window.DOMParser) {
        // Create a DOM parser to handle HTML properly (only works in browser)
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");

        // Get text content from parsed HTML
        const text = doc.body.textContent || doc.body.innerText || "";
        console.log(
          "KeyTermsCloud: Successfully extracted text using DOMParser",
          { textLength: text.length }
        );
        return text;
      } else {
        // Fallback for non-browser environments
        throw new Error("DOMParser not available");
      }
    } catch (error) {
      console.log("KeyTermsCloud: Falling back to regex for HTML extraction", {
        error: error.message,
      });
      // Fallback to regex for simple HTML stripping if DOMParser fails
      const text = html
        .replace(/<[^>]*>?/gm, " ")
        .replace(/&nbsp;/g, " ")
        .replace(/&amp;/g, "&")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"')
        .replace(/&#039;/g, "'")
        .replace(/\s\s+/g, " ")
        .trim();

      console.log("KeyTermsCloud: Text extracted with regex", {
        textLength: text.length,
      });
      return text;
    }
  };

  // Helper function to extract significant words from text
  const extractKeyTerms = (text) => {
    if (!text) {
      console.log("KeyTermsCloud: extractKeyTerms received empty text");
      return [];
    }

    console.log("KeyTermsCloud: extractKeyTerms processing text", {
      textLength: text.length,
    });

    // Strip HTML if the text contains HTML tags
    const plainText = text.includes("<") ? stripHtml(text) : text;

    console.log("KeyTermsCloud: Plain text extracted", {
      plainTextLength: plainText.length,
    });

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
    console.log("KeyTermsCloud: Word extraction", { wordCount: words.length });

    const wordCounts = {};
    words.forEach((word) => {
      if (!commonWords.has(word)) {
        wordCounts[word] = (wordCounts[word] || 0) + 1;
      }
    });

    // Convert to array and sort by frequency
    const result = Object.entries(wordCounts)
      .filter(([_, count]) => count > 1) // Only include words that appear more than once
      .sort((a, b) => b[1] - a[1])
      .slice(0, 50) // Take top 50 terms
      .map(([text, count]) => ({ text, value: count * 5 }));

    console.log("KeyTermsCloud: Final terms extracted", {
      termCount: result.length,
    });
    return result;
  };

  // Handle responsive sizing
  useEffect(() => {
    const calculateSize = () => {
      if (containerRef.current) {
        const parent = containerRef.current.parentElement;
        if (parent) {
          // Use parent container dimensions minus padding
          const containerWidth = parent.clientWidth - 20;
          const containerHeight = Math.min(parent.clientHeight - 20, 350);

          setDimensions({
            width: containerWidth,
            height: containerHeight,
          });
        } else {
          // Fallback if parent not available
          const containerWidth = Math.min(window.innerWidth - 60, 800);
          const containerHeight = Math.min(window.innerHeight - 200, 350);

          setDimensions({
            width: containerWidth,
            height: containerHeight,
          });
        }
      }
    };

    // Calculate initial size
    calculateSize();

    // Add resize event listener
    window.addEventListener("resize", calculateSize);

    // Cleanup
    return () => window.removeEventListener("resize", calculateSize);
  }, []);

  useEffect(() => {
    console.log("KeyTermsCloud: Starting data processing", {
      hasAnalysisData: !!analysisData,
      analysisDataKeys: Object.keys(analysisData || {}),
    });

    // Create a mock data set immediately to avoid endless loading
    const mockData = [
      { text: "Policy", value: 100 },
      { text: "Legislation", value: 80 },
      { text: "Bill", value: 60 },
      { text: "Analysis", value: 40 },
      { text: "Government", value: 30 },
    ];

    const processData = async () => {
      try {
        setIsLoading(true);
        let data = [];

        if (!analysisData) {
          console.log("KeyTermsCloud: No analysis data provided");
          setWordCloudData(mockData);
          setError("No analysis data available");
          setIsLoading(false);
          return;
        }

        console.log("KeyTermsCloud: Analysis data available", {
          hasKeyTerms: !!analysisData.key_terms,
          hasBillText: !!analysisData.bill?.latest_text?.text,
          billTextLength: analysisData.bill?.latest_text?.text?.length || 0,
        });

        // Try to extract from bill text directly first if available
        if (analysisData.bill?.latest_text?.text) {
          console.log("KeyTermsCloud: Found bill text, extracting terms");
          const billText = analysisData.bill.latest_text.text;
          data = extractKeyTerms(billText);
          console.log("KeyTermsCloud: Extracted from bill text", {
            termCount: data.length,
          });
        }
        // Then check for key_terms in analysis data
        else if (analysisData.key_terms) {
          console.log("KeyTermsCloud: Found key_terms in analysis data");
          if (Array.isArray(analysisData.key_terms)) {
            data = analysisData.key_terms.map((item) => ({
              text:
                item.term || item.text || item.word || item.key || String(item),
              value:
                item.score || item.value || item.weight || item.frequency || 10,
            }));
          } else if (typeof analysisData.key_terms === "object") {
            data = Object.entries(analysisData.key_terms).map(
              ([term, score]) => ({
                text: term,
                value: typeof score === "number" ? score * 100 : 10,
              })
            );
          }
          console.log("KeyTermsCloud: Extracted from key_terms", {
            termCount: data.length,
          });
        }
        // Check all other potential sources of data
        else {
          // Check each potential source in turn
          if (data.length === 0 && analysisData.keywords) {
            console.log("KeyTermsCloud: Found keywords in analysis data");
            const terms = Array.isArray(analysisData.keywords)
              ? analysisData.keywords
              : Object.keys(analysisData.keywords);

            data = terms.map((term, index) => ({
              text: typeof term === "string" ? term : String(term),
              value: 100 - index * 5,
            }));
          }

          if (
            data.length === 0 &&
            analysisData.latest_text &&
            analysisData.latest_text.text
          ) {
            console.log("KeyTermsCloud: Found latest_text in analysis data");
            data = extractKeyTerms(analysisData.latest_text.text);
          }

          if (
            data.length === 0 &&
            (analysisData.content ||
              analysisData.summary ||
              analysisData.description)
          ) {
            console.log(
              "KeyTermsCloud: Found content/summary/description in analysis data"
            );
            const text =
              analysisData.content ||
              analysisData.summary ||
              analysisData.description;
            data = extractKeyTerms(text);
          }

          if (data.length === 0 && analysisData.bill_text) {
            console.log("KeyTermsCloud: Found bill_text in analysis data");
            data = extractKeyTerms(analysisData.bill_text);
          }

          console.log("KeyTermsCloud: Extracted from other sources", {
            termCount: data.length,
          });
        }

        // If we still couldn't find any usable data, use fallback
        if (data.length === 0) {
          console.log("KeyTermsCloud: No data found, using fallback");
          data = mockData;
          setError("Could not extract key terms");
        } else {
          setError(null);
        }

        // Sort by value for better visualization
        data.sort((a, b) => b.value - a.value);

        // Limit to reasonable number of terms
        if (data.length > 50) {
          data = data.slice(0, 50);
        }

        console.log("KeyTermsCloud: Final data prepared", {
          termCount: data.length,
        });
        setWordCloudData(data);
      } catch (error) {
        console.error("KeyTermsCloud: Error processing data", error);
        logger.error("Error preparing word cloud data", { error });
        setError("Error processing term data");
        // Use placeholder data if there's an error
        setWordCloudData(mockData);
      } finally {
        setIsLoading(false);
      }
    };

    processData();
  }, [analysisData]);

  // Custom font size calculator - increased sizing for better visibility
  const fontSizeMapper = (word) => {
    // Base size calculation
    const baseSize = Math.log2(word.value) * 6 + 16;

    // Scale based on number of words (fewer words = larger text)
    const scaleFactor = Math.max(0.8, 1.2 - wordCloudData.length / 100);

    return baseSize * scaleFactor;
  };

  // Custom rotation - more words horizontal for better readability
  const rotate = (word) => {
    // Prefer horizontal orientation for better readability
    const random = Math.random();
    return random > 0.8 ? (random > 0.9 ? 90 : -90) : 0;
  };

  // Custom color mapper based on word frequency and theme
  const colorMapper = (word, index) => {
    const baseColors = isDarkMode
      ? ["#60a5fa", "#93c5fd", "#bfdbfe", "#dbeafe", "#eff6ff"] // Blue shades for dark mode
      : ["#1e40af", "#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa"]; // Blue shades for light mode

    // Use word value to determine color intensity - ensure enough variation
    const normalizedValue =
      word.value / Math.max(...wordCloudData.map((w) => w.value));
    const colorIndex = Math.min(
      Math.floor(normalizedValue * baseColors.length),
      baseColors.length - 1
    );

    return baseColors[colorIndex];
  };

  const handleWordClick = (word) => {
    setHoveredWord({
      text: word.text,
      value: word.value,
      x: word.x,
      y: word.y,
    });

    // Hide tooltip after 3 seconds
    setTimeout(() => {
      setHoveredWord(null);
    }, 3000);
  };

  // Debug the container size and force render with fallback data if needed
  const hasValidDimensions = dimensions.width > 0 && dimensions.height > 0;
  console.log("KeyTermsCloud render state:", {
    isLoading,
    hasError: !!error,
    wordCount: wordCloudData.length,
    dimensions,
    hasValidDimensions,
    containerRef: !!containerRef.current,
  });

  // Ensure we have valid dimensions
  if (!hasValidDimensions && containerRef.current) {
    // Force calculate dimensions now
    const width = containerRef.current.clientWidth || 600;
    const height = containerRef.current.clientHeight || 300;
    console.log("KeyTermsCloud: Force setting dimensions", { width, height });
    // Update dimensions immediately
    dimensions.width = width;
    dimensions.height = height;
  }

  // Ensure we render something even if in loading state for too long
  if (isLoading && Date.now() - renderStartTime > 2000) {
    console.log("KeyTermsCloud: Forcing render due to long loading time");
    setIsLoading(false);
    if (wordCloudData.length === 0) {
      setWordCloudData([
        { text: "Policy", value: 100 },
        { text: "Legislation", value: 80 },
        { text: "Bill", value: 60 },
        { text: "Analysis", value: 40 },
        { text: "Government", value: 30 },
      ]);
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64 text-gray-500 dark:text-gray-400">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mr-2"></div>
        Loading key terms...
      </div>
    );
  }

  if (!wordCloudData || wordCloudData.length === 0) {
    return (
      <div className="flex flex-col justify-center items-center h-64 text-gray-500 dark:text-gray-400">
        <FiInfo className="w-8 h-8 mb-2" />
        <p>No key terms data available</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col" ref={containerRef}>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
          Key Terms
        </h3>
        {hoveredWord && (
          <div className="text-sm text-gray-600 dark:text-gray-300 italic">
            {hoveredWord.text}: {Math.round(hoveredWord.value / 1.5)}{" "}
            occurrences
          </div>
        )}
      </div>

      <div className="flex-1 overflow-hidden flex items-center justify-center">
        {isLoading ? (
          <div className="text-center text-gray-500 dark:text-gray-400">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
            <p>Loading key terms...</p>
          </div>
        ) : error ? (
          <div className="text-orange-500 dark:text-orange-400 text-center">
            <FiInfo className="w-6 h-6 mb-2 mx-auto" />
            <p>{error}</p>
            {wordCloudData.length > 0 && (
              <p className="text-sm mt-1">Showing available terms</p>
            )}
          </div>
        ) : wordCloudData.length === 0 ? (
          <div className="text-gray-500 dark:text-gray-400 text-center">
            <FiInfo className="w-6 h-6 mb-2 mx-auto" />
            <p>No key terms data available</p>
          </div>
        ) : (
          <WordCloud
            data={wordCloudData}
            width={Number(dimensions.width) || 500}
            height={Number(dimensions.height) || 300}
            font="Inter, system-ui, Avenir, Helvetica, Arial, sans-serif"
            fontSizeMapper={fontSizeMapper}
            rotate={rotate}
            padding={2}
            onWordMouseOver={(word) => setHoveredWord(word)}
            onWordMouseOut={() => setHoveredWord(null)}
            fill={colorMapper}
          />
        )}
      </div>
    </div>
  );
};

export default KeyTermsCloud;
