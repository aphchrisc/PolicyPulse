import React, { useState, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getLegislation, searchLegislation } from "../services/api";
import { filterBills, getUniqueValues } from "../services/billFilters";
import Breadcrumbs from "../components/navigation/Breadcrumbs";
import logger from "../utils/logger";
import { debounce } from "../utils/helpers";

// Import our new modular components
import BillSearch from "../components/bills/BillSearch";
import BillFilters from "../components/bills/BillFilters";
import BillListTable from "../components/bills/BillListTable";
import BillListCards from "../components/bills/BillListCards";
import Pagination from "../components/bills/Pagination";
import BillsErrorDisplay from "../components/bills/BillsErrorDisplay";
import BillsLoading from "../components/bills/BillsLoading";

// Local storage key for search history
const SEARCH_HISTORY_KEY = "bill_search_history";

// Available page size options
const PAGE_SIZE_OPTIONS = [10, 25, 50];

/**
 * Bills page component for viewing and searching legislation
 */
const BillsPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const queryParams = new URLSearchParams(location.search);

  // Extract URL parameters
  const urlSearchTerm = queryParams.get("search") || "";
  const urlJurisdiction = queryParams.get("jurisdiction") || "all";
  const urlStatus = queryParams.get("status") || "all";
  const urlDateRange = queryParams.get("dateRange") || "all";
  const urlPage = parseInt(queryParams.get("page"), 10) || 1;
  const urlLimit = parseInt(queryParams.get("limit"), 10) || 10; // Default to 10 items per page
  const urlAdvanced = queryParams.get("advanced") === "true";

  // State management
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [bills, setBills] = useState([]);
  const [searchTerm, setSearchTerm] = useState(urlSearchTerm);
  const [showAdvanced, setShowAdvanced] = useState(urlAdvanced);

  // Store search history in state
  const [searchHistory, setSearchHistory] = useState(() => {
    const savedHistory = localStorage.getItem(SEARCH_HISTORY_KEY);
    return savedHistory ? JSON.parse(savedHistory) : [];
  });

  // Advanced search filters
  const [advancedFilters, setAdvancedFilters] = useState(() => {
    return {
      billNumber: queryParams.get("billNumber") || "",
      sponsor: queryParams.get("sponsor") || "",
      subject: queryParams.get("subject") || "",
      fullText: queryParams.get("fullText") || "",
    };
  });

  const [filters, setFilters] = useState({
    jurisdiction: urlJurisdiction,
    status: urlStatus,
    dateRange: urlDateRange,
  });

  const [pagination, setPagination] = useState({
    limit: urlLimit,
    offset: (urlPage - 1) * urlLimit,
    total: 0,
    currentPage: urlPage,
  });

  // Unique values for filter dropdowns (will be populated from API data)
  const [filterOptions, setFilterOptions] = useState({
    jurisdictions: [],
    statuses: [],
    subjects: [],
  });

  // Handle page size change
  const handlePageSizeChange = (newSize) => {
    const newLimit = parseInt(newSize, 10);
    if (PAGE_SIZE_OPTIONS.includes(newLimit)) {
      // Adjust offset to keep user on same content range as much as possible
      const firstItemIndex = (pagination.currentPage - 1) * pagination.limit;
      const newPage = Math.floor(firstItemIndex / newLimit) + 1;

      setPagination({
        ...pagination,
        limit: newLimit,
        offset: (newPage - 1) * newLimit,
        currentPage: newPage,
      });
    }
  };

  // Effect to keep URL and state in sync
  useEffect(() => {
    const params = new URLSearchParams();

    // Only add parameters with values
    if (searchTerm) params.set("search", searchTerm);
    if (filters.jurisdiction !== "all")
      params.set("jurisdiction", filters.jurisdiction);
    if (filters.status !== "all") params.set("status", filters.status);
    if (filters.dateRange !== "all") params.set("dateRange", filters.dateRange);
    if (pagination.currentPage > 1)
      params.set("page", pagination.currentPage.toString());
    if (pagination.limit !== 10)
      // Only include if not default
      params.set("limit", pagination.limit.toString());
    if (showAdvanced) params.set("advanced", "true");

    // Add advanced search params if they exist
    if (advancedFilters.billNumber)
      params.set("billNumber", advancedFilters.billNumber);
    if (advancedFilters.sponsor) params.set("sponsor", advancedFilters.sponsor);
    if (advancedFilters.subject) params.set("subject", advancedFilters.subject);
    if (advancedFilters.fullText)
      params.set("fullText", advancedFilters.fullText);

    // Update URL without triggering navigation effect
    const newUrl = `${location.pathname}?${params.toString()}`;
    if (location.search !== `?${params.toString()}`) {
      navigate(newUrl, { replace: true });
    }
  }, [
    searchTerm,
    filters,
    pagination.currentPage,
    pagination.limit,
    showAdvanced,
    advancedFilters,
  ]);

  // Effect to fetch initial data
  useEffect(() => {
    // Always fetch initial data
    if (urlSearchTerm || showAdvanced) {
      handleSearchWithTerm(urlSearchTerm);
    } else {
      fetchBills();
    }
  }, []); // Empty dependency array means this runs once on mount

  // Effect to handle URL search parameter changes
  useEffect(() => {
    // Only fetch if this is an explicit navigation (not our URL updates)
    if (location.key !== "default") {
      if (urlSearchTerm || showAdvanced) {
        handleSearchWithTerm(urlSearchTerm);
      } else {
        fetchBills();
      }
    }
  }, [location.key]);

  // Update filter options when bills change
  useEffect(() => {
    if (bills.length > 0) {
      setFilterOptions({
        jurisdictions: getUniqueValues(bills, "jurisdiction"),
        statuses: getUniqueValues(bills, "status"),
        subjects: getUniqueValues(bills, "subjects").flat().filter(Boolean),
      });
    }
  }, [bills]);

  // Save search history to localStorage when it changes
  useEffect(() => {
    localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(searchHistory));
  }, [searchHistory]);

  // Fetch all bills
  const fetchBills = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await getLegislation({
        limit: pagination.limit,
        offset: pagination.offset,
        jurisdiction:
          filters.jurisdiction !== "all" ? filters.jurisdiction : undefined,
        status: filters.status !== "all" ? filters.status : undefined,
        date_range: filters.dateRange !== "all" ? filters.dateRange : undefined,
        sort_by: "updated_at", // Sort by most recent first
        sort_direction: "desc",
      });

      if (response && response.data) {
        setBills(response.data.items || []);
        setPagination((prev) => ({
          ...prev,
          total: response.data.count || 0,
        }));
      } else {
        throw new Error("Invalid response format from API");
      }
    } catch (fetchError) {
      // Log the error for debugging
      logger.error("Failed to load bills from API", fetchError);

      // Use a more user-friendly error message with more details
      let errorMessage =
        "Unable to load legislation data. Please try again later or contact support.";

      // Add more specific information if available
      if (fetchError.response) {
        errorMessage += ` (Server responded with status: ${fetchError.response.status})`;
      } else if (fetchError.request) {
        errorMessage += " (No response received from server)";
      } else if (fetchError.message) {
        errorMessage += ` (${fetchError.message})`;
      }

      setError(errorMessage);
      setBills([]);
    } finally {
      setLoading(false);
    }
  };

  // Search for bills by term with debouncing for autosearch
  const debouncedSearch = useCallback(
    debounce((term) => {
      if (term.trim()) {
        navigate(`/bills?search=${encodeURIComponent(term.trim())}`);
        performSearch(term);
      }
    }, 500),
    []
  );

  // Handle input change with debounce
  const handleSearchInputChange = (newTerm) => {
    setSearchTerm(newTerm);
    if (newTerm.trim().length > 2) {
      debouncedSearch(newTerm);
    }
  };

  // Perform the actual search
  const performSearch = async (term) => {
    try {
      setLoading(true);
      setError(null);

      // Skip search if term is empty and not using advanced search
      if (!term.trim() && !showAdvanced) {
        await fetchBills();
        return;
      }

      // Add to search history if not already there
      if (term.trim()) {
        setSearchHistory((prev) => {
          // Avoid duplicates and keep latest 10 searches
          const newHistory = [term, ...prev.filter((t) => t !== term)].slice(
            0,
            10
          );
          return newHistory;
        });
      }

      // Prepare search parameters
      const searchParams = {
        limit: pagination.limit,
        offset: pagination.offset,
        sort_by: "updated_at", // Sort by most recent first
        sort_direction: "desc",
      };

      // Add basic search term if provided
      if (term.trim()) {
        searchParams.keywords = term.trim();
      }

      // Add advanced filters if enabled
      if (showAdvanced) {
        searchParams.filters = {};

        if (advancedFilters.billNumber) {
          searchParams.filters.bill_number = advancedFilters.billNumber;
        }

        if (advancedFilters.sponsor) {
          searchParams.filters.sponsor = advancedFilters.sponsor;
        }

        if (advancedFilters.subject) {
          searchParams.filters.subject = advancedFilters.subject;
        }

        if (advancedFilters.fullText) {
          searchParams.filters.full_text = advancedFilters.fullText;
        }

        // Add standard filters to advanced search
        if (filters.jurisdiction !== "all") {
          searchParams.filters.jurisdiction = filters.jurisdiction;
        }

        if (filters.status !== "all") {
          searchParams.filters.status = filters.status;
        }

        if (filters.dateRange !== "all") {
          searchParams.filters.date_range = filters.dateRange;
        }
      }

      // Execute the search
      const response = await searchLegislation(searchParams);

      if (response && response.data) {
        setBills(response.data.items || []);
        setPagination((prev) => ({
          ...prev,
          offset: 0,
          currentPage: 1,
          total: response.data.count || 0,
        }));
      } else {
        throw new Error("Invalid search response format from API");
      }
    } catch (searchError) {
      // Log the error for debugging
      logger.error("Search API request failed", searchError);

      // Use a more user-friendly error message with more details
      let errorMessage =
        "Search failed. Please try again later or refine your search terms.";

      // Add more specific information if available
      if (searchError.response) {
        errorMessage += ` (Server responded with status: ${searchError.response.status})`;
      } else if (searchError.request) {
        errorMessage += " (No response received from server)";
      } else if (searchError.message) {
        errorMessage += ` (${searchError.message})`;
      }

      setError(errorMessage);
      setBills([]);
    } finally {
      setLoading(false);
    }
  };

  // Search for bills by term (for manual search/form submission)
  const handleSearchWithTerm = async (term) => {
    performSearch(term);
  };

  // Handle search form submission
  const handleSearch = async (e) => {
    e.preventDefault();
    navigate(`/bills?search=${encodeURIComponent(searchTerm.trim())}`);
    performSearch(searchTerm);
  };

  // Toggle advanced search mode
  const toggleAdvanced = () => {
    setShowAdvanced(!showAdvanced);
  };

  // Handle pagination changes
  const handlePageChange = (newPage) => {
    const newOffset = (newPage - 1) * pagination.limit;
    setPagination((prev) => ({
      ...prev,
      offset: newOffset,
      currentPage: newPage,
    }));

    // Fetch new data with updated pagination
    if (searchTerm || showAdvanced) {
      performSearch(searchTerm);
    } else {
      fetchBills();
    }
  };

  // Handle filter changes
  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    setPagination((prev) => ({
      ...prev,
      offset: 0,
      currentPage: 1,
    }));

    // Update data immediately when filters change
    setTimeout(() => {
      if (searchTerm || showAdvanced) {
        performSearch(searchTerm);
      } else {
        fetchBills();
      }
    }, 0);
  };

  // Add retry functionality to handle API errors
  const handleRetry = () => {
    if (searchTerm || showAdvanced) {
      performSearch(searchTerm);
    } else {
      fetchBills();
    }
  };

  // Render loading state
  if (loading && bills.length === 0) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Breadcrumbs
          crumbs={[
            { path: "/", label: "Home" },
            { path: "/bills", label: "Bills", isLast: true },
          ]}
        />
        <h1 className="text-3xl font-bold mb-8">Legislation Tracking</h1>
        <BillsLoading />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <Breadcrumbs
        crumbs={[
          { path: "/", label: "Home" },
          { path: "/bills", label: "Bills", isLast: true },
        ]}
      />

      <h1 className="text-3xl font-bold mb-8">Legislation Tracking</h1>

      {/* Search and Filters Section */}
      <div className="mb-8">
        <BillSearch
          searchTerm={searchTerm}
          setSearchTerm={handleSearchInputChange}
          handleSearch={handleSearch}
          loading={loading}
          showAdvanced={showAdvanced}
          toggleAdvanced={toggleAdvanced}
          advancedFilters={advancedFilters}
          setAdvancedFilters={setAdvancedFilters}
          searchHistory={searchHistory}
        />

        <BillFilters
          filters={filters}
          setFilters={handleFilterChange}
          filterOptions={filterOptions}
        />
      </div>

      {/* Search Summary */}
      {(searchTerm || Object.values(advancedFilters).some((v) => v)) && (
        <div className="mb-4 bg-blue-50 dark:bg-blue-900 p-3 rounded-md">
          <div className="flex justify-between items-center">
            <div>
              <span className="font-medium">Search: </span>
              {searchTerm ? (
                <span className="text-blue-700 dark:text-blue-300">
                  {searchTerm}
                </span>
              ) : (
                <span className="italic text-gray-500 dark:text-gray-400">
                  Advanced search
                </span>
              )}
              {pagination.total > 0 && (
                <span className="ml-2 text-gray-600 dark:text-gray-400">
                  ({pagination.total} results)
                </span>
              )}
            </div>
            <button
              onClick={() => {
                setSearchTerm("");
                setAdvancedFilters({
                  billNumber: "",
                  sponsor: "",
                  subject: "",
                  fullText: "",
                });
                setFilters({
                  jurisdiction: "all",
                  status: "all",
                  dateRange: "all",
                });
                navigate("/bills");
                fetchBills();
              }}
              className="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
            >
              Clear Search
            </button>
          </div>
        </div>
      )}

      {/* Page Size Selector */}
      <div className="flex justify-end mb-4">
        <div className="flex items-center">
          <label className="mr-2 text-sm text-gray-600 dark:text-gray-400">
            Items per page:
          </label>
          <select
            value={pagination.limit}
            onChange={(e) => handlePageSizeChange(e.target.value)}
            className="p-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
          >
            {PAGE_SIZE_OPTIONS.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Loading indicator for subsequent data fetches */}
      {loading && bills.length > 0 && (
        <div className="mb-4 text-center py-2">
          <div className="inline-block animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-blue-500"></div>
          <span className="ml-2 text-blue-600 dark:text-blue-400">
            Updating results...
          </span>
        </div>
      )}

      {/* Error Display */}
      {error && <BillsErrorDisplay message={error} onRetry={handleRetry} />}

      {/* Results Section */}
      {bills.length > 0 ? (
        <>
          {/* Desktop View: Table */}
          <div className="hidden lg:block">
            <BillListTable bills={bills} />
          </div>

          {/* Mobile View: Cards */}
          <div className="block lg:hidden">
            <BillListCards bills={bills} />
          </div>

          {/* Pagination */}
          <Pagination
            currentPage={pagination.currentPage}
            limit={pagination.limit}
            total={pagination.total}
            onPageChange={handlePageChange}
          />
        </>
      ) : !loading && !error ? (
        <div className="text-center p-8 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300">
            No Bills Found
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            No legislation matches your current filters or search criteria.
          </p>
          <button
            onClick={() => {
              setSearchTerm("");
              setAdvancedFilters({
                billNumber: "",
                sponsor: "",
                subject: "",
                fullText: "",
              });
              setFilters({
                jurisdiction: "all",
                status: "all",
                dateRange: "all",
              });
              navigate("/bills");
              fetchBills();
            }}
            className="mt-4 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600"
          >
            Clear Filters
          </button>
        </div>
      ) : null}
    </div>
  );
};

export default BillsPage;
