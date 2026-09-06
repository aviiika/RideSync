/** The "should I wait?" answer. The policy lives on the server; this renders it. */

import { Check, CircleHelp, Clock, TriangleAlert } from 'lucide-react';
import type { ComponentType } from 'react';

import type { Recommendation, RecommendationLevel } from '../../types/domain';

const STYLES: Record<
  RecommendationLevel,
  { className: string; Icon: ComponentType<{ className?: string }> }
> = {
  ARRIVING_SOON: { className: 'bg-positive/10 text-positive', Icon: Check },
  WORTH_WAITING: { className: 'bg-positive/10 text-positive', Icon: Check },
  CONSIDER_WAITING: { className: 'bg-caution/15 text-caution', Icon: Clock },
  LONG_WAIT: { className: 'bg-critical/10 text-critical', Icon: TriangleAlert },
  UNAVAILABLE: { className: 'bg-surface-muted text-muted', Icon: CircleHelp },
};

export function RecommendationPill({
  recommendation,
  showDetail = false,
}: {
  recommendation: Recommendation;
  showDetail?: boolean;
}) {
  const { className, Icon } = STYLES[recommendation.level];

  return (
    <div className="flex flex-col gap-1">
      <span
        className={`inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${className}`}
      >
        <Icon className="h-3.5 w-3.5" />
        {recommendation.label}
      </span>
      {showDetail ? <p className="text-xs text-muted">{recommendation.detail}</p> : null}
    </div>
  );
}
