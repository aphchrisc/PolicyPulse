import React, { useState } from "react";
import ImpactScoreChart from "./ImpactScoreChart";
import ImpactBadge from "../ui/ImpactBadge";
import PrimaryImpactDisplay from "../ui/PrimaryImpactDisplay";

/**
 * Tabbed interface for displaying bill analysis information
 *
 * @param {Object} props - Component props
 * @param {Object} props.analysisData - The analysis data to display
 * @param {string} props.className - Additional CSS classes
 */
const TabbedAnalysisView = ({ analysisData, className = "" }) => {
  const [activeTab, setActiveTab] = useState("summary");

  // Tabs configuration
  const tabs = [
    { id: "summary", label: "Summary" },
    { id: "health", label: "Public Health" },
    { id: "government", label: "Local Government" },
    { id: "economic", label: "Economic" },
    { id: "other", label: "Other Impacts" },
    { id: "actions", label: "Recommended Actions" },
  ];

  // Impact level icon mapper
  const getImpactIcon = (level) => {
    switch (level?.toLowerCase()) {
      case "critical":
        return "🔴";
      case "high":
        return "🟠";
      case "moderate":
        return "🟡";
      case "low":
        return "🔵";
      default:
        return "⚪";
    }
  };

  // Render tab content based on active tab
  const renderTabContent = () => {
    if (!analysisData) {
      return (
        <div className="p-4 text-gray-500 dark:text-gray-400">
          No analysis data available for this bill.
        </div>
      );
    }

    switch (activeTab) {
      case "summary":
        return (
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-semibold mb-4">Bill Summary</h3>
                <p className="mb-4">
                  {analysisData.summary || "No summary available."}
                </p>

                <div className="mb-6">
                  <div className="flex justify-between items-center mb-3">
                    <h4 className="font-medium text-gray-700 dark:text-gray-300">
                      Primary Impact
                    </h4>
                    {analysisData.impact_summary?.impact_level && (
                      <ImpactBadge
                        impact={
                          analysisData.impact_summary.impact_level || "Unknown"
                        }
                      />
                    )}
                  </div>

                  {analysisData.impact_summary ? (
                    <div className="space-y-3">
                      <div className="flex items-center">
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400 w-32">
                          Category:
                        </span>
                        <span className="text-sm ml-2">
                          {analysisData.impact_summary.primary_category?.replace(
                            "_",
                            " "
                          ) || "Not specified"}
                        </span>
                      </div>

                      {analysisData.impact_summary.primary_details && (
                        <div className="flex items-center">
                          <span className="text-sm font-medium text-gray-600 dark:text-gray-400 w-32">
                            Details:
                          </span>
                          <PrimaryImpactDisplay
                            impactDetails={
                              analysisData.impact_summary.primary_details
                            }
                            className="ml-2"
                          />
                        </div>
                      )}

                      <div className="flex items-center">
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400 w-32">
                          Texas Relevance:
                        </span>
                        <span className="text-sm ml-2">
                          {analysisData.impact_summary.relevance_to_texas ||
                            "Not specified"}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No impact summary available.
                    </p>
                  )}
                </div>

                <h4 className="font-medium mt-6 mb-2">Key Points</h4>
                {analysisData.key_points &&
                analysisData.key_points.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-2">
                    {analysisData.key_points.map((item, index) => (
                      <li
                        key={index}
                        className={`
                        ${
                          item.impact_type === "positive"
                            ? "text-green-700 dark:text-green-400"
                            : item.impact_type === "negative"
                            ? "text-red-700 dark:text-red-400"
                            : "text-gray-700 dark:text-gray-300"
                        }
                      `}
                      >
                        {item.point}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 dark:text-gray-400">
                    No key points available.
                  </p>
                )}
              </div>

              <ImpactScoreChart analysisData={analysisData} />
            </div>
          </div>
        );

      case "health":
        return (
          <div className="p-4">
            <h3 className="text-lg font-semibold mb-4">
              Public Health Impacts
            </h3>

            {analysisData.public_health_impacts ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium mb-2">Direct Effects</h4>
                  {analysisData.public_health_impacts.direct_effects &&
                  analysisData.public_health_impacts.direct_effects.length >
                    0 ? (
                    <ul className="list-disc pl-5 space-y-2">
                      {analysisData.public_health_impacts.direct_effects.map(
                        (effect, index) => (
                          <li key={index}>{effect}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No direct effects identified.
                    </p>
                  )}

                  <h4 className="font-medium mt-6 mb-2">Indirect Effects</h4>
                  {analysisData.public_health_impacts.indirect_effects &&
                  analysisData.public_health_impacts.indirect_effects.length >
                    0 ? (
                    <ul className="list-disc pl-5 space-y-2">
                      {analysisData.public_health_impacts.indirect_effects.map(
                        (effect, index) => (
                          <li key={index}>{effect}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No indirect effects identified.
                    </p>
                  )}
                </div>

                <div>
                  <h4 className="font-medium mb-2">Funding Impact</h4>
                  {analysisData.public_health_impacts.funding_impact &&
                  analysisData.public_health_impacts.funding_impact.length >
                    0 ? (
                    <ul className="list-disc pl-5 space-y-2">
                      {analysisData.public_health_impacts.funding_impact.map(
                        (impact, index) => (
                          <li key={index}>{impact}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No funding impacts identified.
                    </p>
                  )}

                  <h4 className="font-medium mt-6 mb-2">
                    Vulnerable Populations
                  </h4>
                  {analysisData.public_health_impacts.vulnerable_populations &&
                  analysisData.public_health_impacts.vulnerable_populations
                    .length > 0 ? (
                    <ul className="list-disc pl-5 space-y-2">
                      {analysisData.public_health_impacts.vulnerable_populations.map(
                        (population, index) => (
                          <li key={index}>{population}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No vulnerable populations identified.
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">
                No public health impacts available.
              </p>
            )}
          </div>
        );

      case "government":
        return (
          <div className="p-4">
            <h3 className="text-lg font-semibold mb-4">
              Local Government Impacts
            </h3>

            {analysisData.local_government_impacts ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <h4 className="font-medium mb-2">Administrative</h4>
                  {analysisData.local_government_impacts.administrative &&
                  analysisData.local_government_impacts.administrative.length >
                    0 ? (
                    <ul className="list-disc pl-5 space-y-2">
                      {analysisData.local_government_impacts.administrative.map(
                        (item, index) => (
                          <li key={index}>{item}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No administrative impacts identified.
                    </p>
                  )}
                </div>

                <div>
                  <h4 className="font-medium mb-2">Fiscal</h4>
                  {analysisData.local_government_impacts.fiscal &&
                  analysisData.local_government_impacts.fiscal.length > 0 ? (
                    <ul className="list-disc pl-5 space-y-2">
                      {analysisData.local_government_impacts.fiscal.map(
                        (item, index) => (
                          <li key={index}>{item}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No fiscal impacts identified.
                    </p>
                  )}
                </div>

                <div>
                  <h4 className="font-medium mb-2">Implementation</h4>
                  {analysisData.local_government_impacts.implementation &&
                  analysisData.local_government_impacts.implementation.length >
                    0 ? (
                    <ul className="list-disc pl-5 space-y-2">
                      {analysisData.local_government_impacts.implementation.map(
                        (item, index) => (
                          <li key={index}>{item}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No implementation impacts identified.
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">
                No local government impacts available.
              </p>
            )}
          </div>
        );

      case "economic":
        return (
          <div className="p-4">
            <h3 className="text-lg font-semibold mb-4">Economic Impacts</h3>

            {analysisData.economic_impacts ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium mb-2">Direct Costs</h4>
                  {analysisData.economic_impacts.direct_costs &&
                  analysisData.economic_impacts.direct_costs.length > 0 ? (
                    <ul className="list-disc pl-5 space-y-2">
                      {analysisData.economic_impacts.direct_costs.map(
                        (item, index) => (
                          <li key={index}>{item}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No direct costs identified.
                    </p>
                  )}

                  <h4 className="font-medium mt-6 mb-2">Economic Effects</h4>
                  {analysisData.economic_impacts.economic_effects &&
                  analysisData.economic_impacts.economic_effects.length > 0 ? (
                    <ul className="list-disc pl-5 space-y-2">
                      {analysisData.economic_impacts.economic_effects.map(
                        (item, index) => (
                          <li key={index}>{item}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No economic effects identified.
                    </p>
                  )}
                </div>

                <div>
                  <h4 className="font-medium mb-2">Benefits</h4>
                  {analysisData.economic_impacts.benefits &&
                  analysisData.economic_impacts.benefits.length > 0 ? (
                    <ul className="list-disc pl-5 space-y-2">
                      {analysisData.economic_impacts.benefits.map(
                        (item, index) => (
                          <li key={index}>{item}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No benefits identified.
                    </p>
                  )}

                  <h4 className="font-medium mt-6 mb-2">Long-term Impact</h4>
                  {analysisData.economic_impacts.long_term_impact &&
                  analysisData.economic_impacts.long_term_impact.length > 0 ? (
                    <ul className="list-disc pl-5 space-y-2">
                      {analysisData.economic_impacts.long_term_impact.map(
                        (item, index) => (
                          <li key={index}>{item}</li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="text-gray-500 dark:text-gray-400">
                      No long-term impacts identified.
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">
                No economic impacts available.
              </p>
            )}
          </div>
        );

      case "other":
        return (
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <h3 className="text-lg font-semibold mb-4">
                  Environmental Impacts
                </h3>
                {analysisData.environmental_impacts &&
                analysisData.environmental_impacts.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-2">
                    {analysisData.environmental_impacts.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 dark:text-gray-400">
                    No environmental impacts identified.
                  </p>
                )}
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-4">
                  Education Impacts
                </h3>
                {analysisData.education_impacts &&
                analysisData.education_impacts.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-2">
                    {analysisData.education_impacts.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 dark:text-gray-400">
                    No education impacts identified.
                  </p>
                )}
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-4">
                  Infrastructure Impacts
                </h3>
                {analysisData.infrastructure_impacts &&
                analysisData.infrastructure_impacts.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-2">
                    {analysisData.infrastructure_impacts.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 dark:text-gray-400">
                    No infrastructure impacts identified.
                  </p>
                )}
              </div>
            </div>
          </div>
        );

      case "actions":
        return (
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <h3 className="text-lg font-semibold mb-4">
                  Recommended Actions
                </h3>
                {analysisData.recommended_actions &&
                analysisData.recommended_actions.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-2">
                    {analysisData.recommended_actions.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 dark:text-gray-400">
                    No recommended actions identified.
                  </p>
                )}
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-4">
                  Immediate Actions
                </h3>
                {analysisData.immediate_actions &&
                analysisData.immediate_actions.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-2">
                    {analysisData.immediate_actions.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 dark:text-gray-400">
                    No immediate actions identified.
                  </p>
                )}
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-4">Resource Needs</h3>
                {analysisData.resource_needs &&
                analysisData.resource_needs.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-2">
                    {analysisData.resource_needs.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 dark:text-gray-400">
                    No resource needs identified.
                  </p>
                )}
              </div>
            </div>
          </div>
        );

      default:
        return (
          <div className="p-4 text-gray-500 dark:text-gray-400">
            Select a tab to view analysis details.
          </div>
        );
    }
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow ${className}`}>
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap ${
                activeTab === tab.id
                  ? "border-b-2 border-blue-500 text-blue-600 dark:text-blue-400"
                  : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="tab-content">{renderTabContent()}</div>
    </div>
  );
};

export default TabbedAnalysisView;
