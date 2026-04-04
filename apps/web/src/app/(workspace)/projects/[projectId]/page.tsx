import { ProjectDetailScreen } from "@/features/projects/components/project-detail-screen";

interface ProjectDetailPageProps {
  params: Promise<{ projectId: string }>;
}

export default async function ProjectDetailPage({ params }: ProjectDetailPageProps) {
  const { projectId } = await params;

  return <ProjectDetailScreen projectId={projectId} />;
}
