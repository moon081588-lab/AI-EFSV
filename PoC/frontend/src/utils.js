export const formatPercent = (value) => `${Number(value ?? 0).toFixed(1)}%`;
export const formatConfidence = (value) => `${(Number(value ?? 0) * 100).toFixed(1)}%`;
export const formatHours = (minutes) => `${(Number(minutes ?? 0) / 60).toFixed(1)} h`;

export const ASIL_ORDER = ['QM', 'A', 'B', 'C', 'D'];

export const getRequirementIdFromRow = (row) => (
  row?.requirement_id ??
  row?.requirementId ??
  row?.RequirementID ??
  row?.requirementID ??
  row?.requirement_id_raw ??
  row?.requirementIdRaw
);

export const getTestCaseIdFromRow = (row) => (
  row?.matched_test_case_id ??
  row?.testCaseId ??
  row?.test_case_id ??
  row?.matchedTestCaseId
);

export const getAsilFromRow = (row) => String(row?.asil_level ?? row?.asilLevel ?? 'QM').toUpperCase();
export const getMatchScoreFromRow = (row) => Number(row?.match_score ?? row?.confidence ?? row?.final_match_score ?? 0);
export const getTestDurationFromRow = (row) => Number(row?.test_duration_minutes ?? row?.durationMinutes ?? row?.estimatedDurationMinutes ?? 0);
export const getCoverageTypeFromRow = (row) => String(row?.coverage_type ?? row?.coverageType ?? '').toLowerCase();

export const isMappingReviewRequiredRow = (row) => {
  const reviewStatus = String(row?.reviewStatus ?? row?.review_status ?? '').toUpperCase();
  const mappingReviewStatus = String(row?.mappingReviewStatus ?? row?.mapping_review_status ?? '').toUpperCase();
  return (
    reviewStatus === 'MANUAL_REVIEW_REQUIRED' ||
    reviewStatus === 'REVIEW_REQUIRED' ||
    reviewStatus === 'WEAK_FALLBACK' ||
    reviewStatus === 'EXTERNAL_VALIDATION_REQUIRED' ||
    mappingReviewStatus === 'MAPPING_REVIEW_REQUIRED'
  );
};

export function normalizeSummary(rawSummary = {}, activeSummary = {}, activeMatches = [], activeReviewItems = []) {
  const requirementIds = new Set(activeMatches.map(getRequirementIdFromRow).filter(Boolean));
  const uniqueTests = new Map();
  activeMatches.forEach((row) => {
    const testCaseId = getTestCaseIdFromRow(row);
    if (testCaseId && !uniqueTests.has(testCaseId)) uniqueTests.set(testCaseId, row);
  });

  const rawRequirementsUploaded = Number(
    activeSummary.requirementsUploaded ??
    rawSummary.requirementsUploaded ??
    rawSummary.totalRequirements ??
    rawSummary.requirementCount ??
    requirementIds.size
  );
  const totalRequirements = Number(activeSummary.totalRequirements ?? activeSummary.requirementCount ?? requirementIds.size);
  const mappingCount = Number(activeSummary.mappingCount ?? activeSummary.requirementTestMappings ?? activeMatches.length);
  const uniqueTestCases = Number(activeSummary.uniqueTestCases ?? activeSummary.uniqueTestCaseCount ?? uniqueTests.size);
  const totalTestTimeMinutes = Number(
    activeSummary.totalTestTimeMinutes ??
    activeSummary.estimatedTestTimeMinutes ??
    activeSummary.totalEstimatedTestTimeMinutes ??
    Array.from(uniqueTests.values()).reduce((sum, row) => sum + getTestDurationFromRow(row), 0)
  );
  const reviewRequirementIds = new Set(activeReviewItems.map(getRequirementIdFromRow).filter(Boolean));
  const reviewNeeded = Number(
    activeSummary.reviewNeeded ??
    activeSummary.reviewNeededCount ??
    activeSummary.reviewNeededRequirements ??
    reviewRequirementIds.size
  );
  const averageConfidence = Number(
    activeSummary.averageConfidence ??
    activeSummary.avgMatchScore ??
    (activeMatches.length
      ? activeMatches.reduce((sum, row) => sum + getMatchScoreFromRow(row), 0) / activeMatches.length
      : 0)
  );

  const requirementAsil = new Map();
  activeMatches.forEach((row) => {
    const requirementId = getRequirementIdFromRow(row);
    if (requirementId) requirementAsil.set(requirementId, getAsilFromRow(row));
  });
  const requirementCountsByAsil = ASIL_ORDER.map((asilLevel) => ({
    asilLevel,
    count: Array.from(requirementAsil.values()).filter((level) => level === asilLevel).length,
  }));
  const reviewNeededByAsil = ASIL_ORDER.map((asilLevel) => ({
    asilLevel,
    reviewNeeded: new Set(
      activeReviewItems.filter((row) => getAsilFromRow(row) === asilLevel).map(getRequirementIdFromRow).filter(Boolean)
    ).size,
  }));
  const coverageByAsil = requirementCountsByAsil.map(({ asilLevel, count }) => {
    const rawCount = Number((rawSummary.requirementCountsByAsil ?? rawSummary.asilCounts ?? [])
      .find((item) => item.asilLevel === asilLevel)?.count ?? count);
    return {
      asilLevel,
      requirements: rawCount,
      covered: count,
      coverageRate: rawCount > 0 ? Math.round((count / rawCount) * 1000) / 10 : 0,
    };
  });
  const estimatedTestTimeByAsil = ASIL_ORDER.map((asilLevel) => ({
    asilLevel,
    estimatedMinutes: Array.from(uniqueTests.values())
      .filter((row) => getAsilFromRow(row) === asilLevel)
      .reduce((sum, row) => sum + getTestDurationFromRow(row), 0),
  }));
  const testTypeCounts = Array.from(uniqueTests.values()).reduce((counts, row) => {
    const testType = String(row?.test_type ?? row?.testType ?? 'Unknown');
    const existing = counts.find((item) => item.testType === testType);
    if (existing) existing.count += 1;
    else counts.push({ testType, count: 1 });
    return counts;
  }, []);
  const confidenceDistribution = [
    { label: 'High (>= 0.80)', status: 'good', count: activeMatches.filter((row) => getMatchScoreFromRow(row) >= 0.8).length },
    { label: 'Medium (0.65-0.79)', status: 'warning', count: activeMatches.filter((row) => getMatchScoreFromRow(row) >= 0.65 && getMatchScoreFromRow(row) < 0.8).length },
    { label: 'Low (< 0.65)', status: 'danger', count: activeMatches.filter((row) => getMatchScoreFromRow(row) < 0.65).length },
  ];
  const reviewItems = activeReviewItems.map((row) => ({
    requirementId: getRequirementIdFromRow(row),
    asilLevel: getAsilFromRow(row),
    matchedTestCaseId: getTestCaseIdFromRow(row),
    matchedTestCaseName: row?.matched_test_case_name ?? row?.testCaseName ?? row?.generatedCandidateTestCase?.testCaseName ?? 'Pending verification evidence',
    confidence: getMatchScoreFromRow(row),
    action: getCoverageTypeFromRow(row) === 'external_validation_required' ? 'External Validation' : 'Manual Review',
  }));
  const longestTests = Array.from(uniqueTests.values())
    .map((row) => ({
      testCaseId: getTestCaseIdFromRow(row),
      testCaseName: row?.matched_test_case_name ?? row?.testCaseName ?? 'Unnamed test case',
      testType: row?.test_type ?? row?.testType ?? 'Unknown',
      durationMinutes: getTestDurationFromRow(row),
    }))
    .sort((a, b) => b.durationMinutes - a.durationMinutes)
    .slice(0, 10);
  const highRiskRequirementCount = new Set(
    activeMatches.filter((row) => ['C', 'D'].includes(getAsilFromRow(row))).map(getRequirementIdFromRow).filter(Boolean)
  ).size;
  const coverageRate = Number(
    activeSummary.coverageRate ??
    (rawRequirementsUploaded > 0 ? Math.round((totalRequirements / rawRequirementsUploaded) * 1000) / 10 : 0)
  );
  const testReuseRatio = Number(
    activeSummary.testReuseRatio ??
    (uniqueTestCases > 0 ? Math.round((mappingCount / uniqueTestCases) * 100) / 100 : 0)
  );
  const highestAsilLevel = [...ASIL_ORDER].reverse().find((level) => requirementCountsByAsil.find((row) => row.asilLevel === level)?.count > 0) ?? 'N/A';
  const executiveSummary = (
    `${totalRequirements} of ${rawRequirementsUploaded} uploaded requirements are currently eligible for active evidence, ` +
    `using ${uniqueTestCases} unique test cases and ${mappingCount} active mappings. ` +
    `${reviewNeeded} requirement(s) remain visible in the review queue.`
  );

  return {
    ...rawSummary,
    ...activeSummary,
    rawRequirementsUploaded,
    requirementsUploaded: totalRequirements,
    totalRequirements,
    requirementCount: totalRequirements,
    requirementTestMappings: mappingCount,
    mappingCount,
    uniqueTestCases,
    uniqueTestCaseCount: uniqueTestCases,
    totalTestTimeMinutes,
    estimatedTestTimeMinutes: totalTestTimeMinutes,
    totalEstimatedTestTimeMinutes: totalTestTimeMinutes,
    reviewNeededRequirements: reviewNeeded,
    reviewNeeded,
    reviewNeededCount: reviewNeeded,
    highRiskRequirementCount,
    highRiskRequirements: highRiskRequirementCount,
    averageConfidence,
    avgMatchScore: averageConfidence,
    averageMatchScore: averageConfidence,
    coverageRate,
    testReuseRatio,
    highestAsilLevel,
    requirementCountsByAsil,
    asilCounts: requirementCountsByAsil,
    testTypeCounts,
    coverageByAsil,
    estimatedTestTimeByAsil,
    reviewNeededByAsil,
    confidenceDistribution,
    reviewItems,
    longestTests,
    requirementsFullyCovered: totalRequirements,
    uncoveredRequirements: Math.max(rawRequirementsUploaded - totalRequirements, 0),
    executiveSummary,
  };
}

export const MAPPING_REVIEW_REASON_LABELS = {
  LOW_MATCH_SCORE: 'Low match score',
  AMBIGUOUS_REQUIREMENT: 'Ambiguous requirement',
  WEAK_DOMAIN_ALIGNMENT: 'Weak domain alignment',
  MISSING_EXPECTED_RESPONSE: 'Missing expected response',
  NO_STRONG_HISTORICAL_TEST: 'No strong historical test',
};

export const formatMappingReviewReasonCode = (code) => (
  MAPPING_REVIEW_REASON_LABELS[code] || String(code || '').replaceAll('_', ' ').toLowerCase()
);

export const asilColorClass = (asilLevel) => {
  const level = String(asilLevel || '').toUpperCase();
  if (level === 'D') return 'asil-d';
  if (level === 'C') return 'asil-c';
  if (level === 'B') return 'asil-b';
  if (level === 'A') return 'asil-a';
  return 'asil-qm';
};
