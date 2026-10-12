export type BaseProject = {
  base_sha: string;
  milestones: Array<{reviews: Array<{evidence?: {base_sha?: string}}>}>;
};

export function baseLabels(project: BaseProject) {
  const initial = project.milestones[0]?.reviews[0]?.evidence?.base_sha ?? project.base_sha;
  return {initial, current: project.base_sha, advanced: initial !== project.base_sha};
}
