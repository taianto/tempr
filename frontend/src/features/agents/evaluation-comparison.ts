import { CATEGORIES } from "./classification-categories";
import type { EvaluationResult, TestSuiteEvaluation, TestSuiteItem } from "./types";

export const RUBRIC_DIMENSIONS = [
  { key: "adherence", label: "Adherence" },
  { key: "consistency", label: "Consistency" },
  { key: "grounding", label: "Grounding" },
] as const;

type RubricKey = (typeof RUBRIC_DIMENSIONS)[number]["key"];
type RubricScoreKey = `${RubricKey}_score`;

export type CategoryEvaluationAggregate = {
  count: number;
  average: number;
} & Record<RubricKey, number>;

export type EvaluationAggregate = Record<string, CategoryEvaluationAggregate>;

export function compareScores(
  value: number,
  reference: number | undefined,
): "higher" | "lower" | undefined {
  if (reference === undefined || value === reference) return undefined;
  return value > reference ? "higher" : "lower";
}

function score(result: EvaluationResult, key: RubricKey) {
  return result[`${key}_score` as RubricScoreKey];
}

export function aggregateEvaluation(
  items: TestSuiteItem[],
  evaluation: TestSuiteEvaluation,
): EvaluationAggregate | undefined {
  if (evaluation.status !== "completed" || items.length === 0) return undefined;
  if (evaluation.results.length !== items.length) return undefined;

  const expected = new Map(items.map((item) => [item.id, item.category]));
  const results = new Map(evaluation.results.map((result) => [result.test_case_id, result]));
  if (results.size !== items.length) return undefined;
  for (const [id, category] of expected) {
    if (results.get(id)?.category !== category) return undefined;
  }

  const aggregates: Record<string, { count: number; total: number } & Record<RubricKey, number>> =
    {};
  for (const category of CATEGORIES.map((item) => item.key)) {
    aggregates[category] = { count: 0, total: 0, adherence: 0, consistency: 0, grounding: 0 };
  }

  for (const result of evaluation.results) {
    const aggregate = aggregates[result.category];
    if (!aggregate) return undefined;
    aggregate.count += 1;
    for (const dimension of RUBRIC_DIMENSIONS) {
      aggregate[dimension.key] += score(result, dimension.key);
    }
    aggregate.total +=
      RUBRIC_DIMENSIONS.reduce((total, dimension) => total + score(result, dimension.key), 0) /
      RUBRIC_DIMENSIONS.length;
  }

  return Object.fromEntries(
    Object.entries(aggregates).map(([category, aggregate]) => [
      category,
      {
        count: aggregate.count,
        average: aggregate.count ? aggregate.total / aggregate.count : 0,
        adherence: aggregate.adherence / aggregate.count,
        consistency: aggregate.consistency / aggregate.count,
        grounding: aggregate.grounding / aggregate.count,
      },
    ]),
  );
}
