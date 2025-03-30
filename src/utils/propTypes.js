import PropTypes from "prop-types";

/**
 * Common PropTypes for analysis data used across components
 */
export const analysisPropTypes = {
  // Basic analysis data structure
  analysisData: PropTypes.shape({
    summary: PropTypes.string,
    key_points: PropTypes.arrayOf(PropTypes.string),
    potential_impacts: PropTypes.arrayOf(PropTypes.string),
    sentiment: PropTypes.shape({
      score: PropTypes.number,
      explanation: PropTypes.string,
      toFixed: PropTypes.func,
    }),
    topics: PropTypes.arrayOf(
      PropTypes.shape({
        text: PropTypes.string,
        value: PropTypes.number,
      })
    ),
    impact_summary: PropTypes.shape({
      impact_level: PropTypes.string,
      primary_category: PropTypes.string,
      primary_details: PropTypes.string,
      relevance_to_texas: PropTypes.string,
    }),
    public_health_impacts: PropTypes.shape({
      direct_effects: PropTypes.arrayOf(PropTypes.string),
      indirect_effects: PropTypes.arrayOf(PropTypes.string),
      funding_impact: PropTypes.arrayOf(PropTypes.string),
      vulnerable_populations: PropTypes.arrayOf(PropTypes.string),
    }),
    local_government_impacts: PropTypes.shape({
      administrative: PropTypes.arrayOf(PropTypes.string),
      fiscal: PropTypes.arrayOf(PropTypes.string),
      implementation: PropTypes.arrayOf(PropTypes.string),
    }),
    economic_impacts: PropTypes.shape({
      direct_costs: PropTypes.arrayOf(PropTypes.string),
      economic_effects: PropTypes.arrayOf(PropTypes.string),
      benefits: PropTypes.arrayOf(PropTypes.string),
      long_term_impact: PropTypes.arrayOf(PropTypes.string),
    }),
    environmental_impacts: PropTypes.arrayOf(PropTypes.string),
    education_impacts: PropTypes.arrayOf(PropTypes.string),
    infrastructure_impacts: PropTypes.arrayOf(PropTypes.string),
    recommended_actions: PropTypes.arrayOf(PropTypes.string),
    immediate_actions: PropTypes.arrayOf(PropTypes.string),
    resource_needs: PropTypes.arrayOf(PropTypes.string),
  }),
};

/**
 * Common PropTypes for bills data used across components
 */
export const billPropTypes = {
  bill: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    title: PropTypes.string,
    status: PropTypes.string,
    introduced_date: PropTypes.string,
    introduced: PropTypes.string,
    lastAction: PropTypes.string,
    history: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string,
        action: PropTypes.string,
      })
    ),
  }),
};

/**
 * Common PropTypes for impact-related components
 */
export const impactPropTypes = {
  impactLevel: PropTypes.oneOf(["high", "medium", "low", "unknown"]),
  impactDetails: PropTypes.shape({
    primaryCategory: PropTypes.string,
    level: PropTypes.string,
    details: PropTypes.string,
  }),
  stakeholders: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      impact: PropTypes.string,
      importance: PropTypes.number,
    })
  ),
  sentiment: PropTypes.shape({
    score: PropTypes.number,
    explanation: PropTypes.string,
  }),
  topics: PropTypes.arrayOf(
    PropTypes.shape({
      text: PropTypes.string,
      value: PropTypes.number,
    })
  ),
};

/**
 * Common PropTypes for UI components
 */
export const uiPropTypes = {
  className: PropTypes.string,
  children: PropTypes.node,
  size: PropTypes.oneOf(["small", "medium", "large"]),
  showText: PropTypes.bool,
  showLabel: PropTypes.bool,
  isLoading: PropTypes.bool,
  message: PropTypes.string,
  height: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  isDarkMode: PropTypes.bool,
};

/**
 * Common PropTypes for notification related components
 */
export const notificationPropTypes = {
  notification: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    type: PropTypes.string,
    title: PropTypes.string,
    message: PropTypes.string,
    timestamp: PropTypes.string,
    read: PropTypes.bool,
    billId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  }),
};

/**
 * Common PropTypes for context providers
 */
export const contextPropTypes = {
  children: PropTypes.node,
};

export default {
  analysisPropTypes,
  billPropTypes,
  impactPropTypes,
  uiPropTypes,
  notificationPropTypes,
  contextPropTypes,
};
