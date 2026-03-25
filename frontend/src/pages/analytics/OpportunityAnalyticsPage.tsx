/** Steps 246–248: Opportunity analytics – saved searches, discovery alert rules, opportunity timeline. */
import SavedSearchPanel from '../../components/analytics/SavedSearchPanel'
import DiscoveryAlertRulesPanel from '../../components/analytics/DiscoveryAlertRulesPanel'
import OpportunityTimeline from '../../components/analytics/OpportunityTimeline'

export interface OpportunityAnalyticsPageProps {
  workspaceId: number
  opportunityId: number
}

export default function OpportunityAnalyticsPage({ workspaceId, opportunityId }: OpportunityAnalyticsPageProps) {
  return (
    <div>
      <h2 style={{ margin: '0 0 1rem', fontSize: '1.1rem' }}>Opportunity analytics</h2>
      <SavedSearchPanel workspaceId={workspaceId} />
      <DiscoveryAlertRulesPanel workspaceId={workspaceId} />
      <OpportunityTimeline workspaceId={workspaceId} opportunityId={opportunityId} />
    </div>
  )
}
