/**
 * Common PropTypes for reuse across components
 * This centralizes common prop type definitions to reduce repetition and improve consistency
 */
import PropTypes from "prop-types";

// Common UI prop types
export const uiPropTypes = {
  children: PropTypes.node,
  className: PropTypes.string,
  style: PropTypes.object,
};

// Common data structure prop types
export const impactPropTypes = {
  impact: PropTypes.string.isRequired,
  impactLevel: PropTypes.string,
  impactDetails: PropTypes.shape({
    type: PropTypes.string,
    level: PropTypes.string,
    description: PropTypes.string,
    category: PropTypes.string,
  }),
};

export const billPropTypes = {
  bill: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    title: PropTypes.string,
    status: PropTypes.string,
    introduced_date: PropTypes.string,
    introduced: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.instanceOf(Date),
    ]),
    lastAction: PropTypes.string,
    history: PropTypes.array,
  }),
};

export const analysisDataPropTypes = {
  analysisData: PropTypes.shape({
    summary: PropTypes.string,
    key_points: PropTypes.array,
    topics: PropTypes.array,
    impact_summary: PropTypes.shape({
      impact_level: PropTypes.string,
      primary_category: PropTypes.string,
      primary_details: PropTypes.string,
      relevance_to_texas: PropTypes.string,
    }),
    public_health_impacts: PropTypes.shape({
      direct_effects: PropTypes.array,
      indirect_effects: PropTypes.array,
      funding_impact: PropTypes.array,
      vulnerable_populations: PropTypes.array,
    }),
    local_government_impacts: PropTypes.shape({
      administrative: PropTypes.array,
      fiscal: PropTypes.array,
      implementation: PropTypes.array,
    }),
    economic_impacts: PropTypes.shape({
      direct_costs: PropTypes.array,
      economic_effects: PropTypes.array,
      benefits: PropTypes.array,
      long_term_impact: PropTypes.array,
    }),
    environmental_impacts: PropTypes.array,
    education_impacts: PropTypes.array,
    infrastructure_impacts: PropTypes.array,
    recommended_actions: PropTypes.array,
    immediate_actions: PropTypes.array,
    resource_needs: PropTypes.array,
  }),
};

export const stakeholderPropTypes = {
  stakeholders: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      type: PropTypes.string,
      impact: PropTypes.string,
      position: PropTypes.string,
    })
  ),
};

export const sentimentPropTypes = {
  sentiment: PropTypes.shape({
    score: PropTypes.number,
    explanation: PropTypes.string,
  }),
};

// Export common shape validators for reuse
export const shapes = {
  bill: billPropTypes.bill,
  analysisData: analysisDataPropTypes.analysisData,
  stakeholders: stakeholderPropTypes.stakeholders,
  sentiment: sentimentPropTypes.sentiment,
};

// Export default combinations for common component patterns
export default {
  ui: uiPropTypes,
  bill: billPropTypes,
  analysisData: analysisDataPropTypes,
  stakeholders: stakeholderPropTypes,
  sentiment: sentimentPropTypes,
  shapes,
};
