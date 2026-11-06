import { describe, expect, it } from "vitest";
import { aggregateEvaluation, compareScores } from "./evaluation-comparison";
import type { TestSuiteEvaluation, TestSuiteItem } from "./types";

const items: TestSuiteItem[] = [
  { id: "case-1", category: "happy_path", question: "q1", expected_behavior: "e1" },
  { id: "case-2", category: "happy_path", question: "q2", expected_behavior: "e2" },
  { id: "case-3", category: "boundary_probe", question: "q3", expected_behavior: "e3" },
];

function result(
  id: string,
  category: string,
  adherence: number,
  consistency: number,
  grounding: number,
) {
  return {
    id: `result-${id}`,
    test_case_id: id,
    category,
    adherence_score: adherence,
    consistency_score: consistency,
    grounding_score: grounding,
    adherence_explanation: "adherence",
    consistency_explanation: "consistency",
    grounding_explanation: "grounding",
  };
}

function evaluation(results: TestSuiteEvaluation["results"]): TestSuiteEvaluation {
  return {
    id: "evaluation-1",
    test_suite_id: "suite-1",
    trace_id: "trace-1",
    status: "completed",
    judge_model: "judge",
    rubric_version: "1",
    classification_snapshot: {},
    error: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    results,
  };
}

describe("aggregateEvaluation", () => {
  it("averages all rubric dimensions equally per case and then across each category", () => {
    const aggregate = aggregateEvaluation(
      items,
      evaluation([
        result("case-1", "happy_path", 1, 0.5, 0),
        result("case-2", "happy_path", 0.5, 1, 1),
        result("case-3", "boundary_probe", 0, 0, 1),
      ]),
    );

    expect(aggregate?.happy_path).toEqual({
      count: 2,
      average: (0.5 + 2.5 / 3) / 2,
      adherence: 0.75,
      consistency: 0.75,
      grounding: 0.5,
    });
    expect(aggregate?.boundary_probe).toEqual({
      count: 1,
      average: 1 / 3,
      adherence: 0,
      consistency: 0,
      grounding: 1,
    });
  });

  it("keeps zero scores and rejects incomplete or mismatched results", () => {
    const zero = result("case-1", "happy_path", 0, 0, 0);
    expect(aggregateEvaluation([items[0]], evaluation([zero]))?.happy_path.average).toBe(0);
    expect(aggregateEvaluation(items, evaluation([zero]))).toBeUndefined();
    expect(
      aggregateEvaluation([items[0]], evaluation([result("case-1", "boundary_probe", 1, 1, 1)])),
    ).toBeUndefined();
  });

  it("returns no aggregate for an empty suite", () => {
    expect(aggregateEvaluation([], evaluation([]))).toBeUndefined();
  });
});

describe("compareScores", () => {
  it("reports higher and lower scores, with no direction for ties or missing references", () => {
    expect(compareScores(0.8, 0.5)).toBe("higher");
    expect(compareScores(0.2, 0.5)).toBe("lower");
    expect(compareScores(0.5, 0.5)).toBeUndefined();
    expect(compareScores(0.5, undefined)).toBeUndefined();
  });
});
