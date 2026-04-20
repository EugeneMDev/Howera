import { ProjectJobsScreen } from "@/features/jobs/components/project-jobs-screen";

interface ProjectJobsPageProps {
  params: Promise<{ projectId: string }>;
}

export default async function ProjectJobsPage({ params }: ProjectJobsPageProps) {
  const { projectId } = await params;

  return <ProjectJobsScreen projectId={projectId} />;
}
