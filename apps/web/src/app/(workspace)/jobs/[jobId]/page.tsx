import { JobDetailScreen } from "@/features/jobs/components/job-detail-screen";

interface JobDetailPageProps {
  params: Promise<{ jobId: string }>;
}

export default async function JobDetailPage({ params }: JobDetailPageProps) {
  const { jobId } = await params;

  return <JobDetailScreen jobId={jobId} />;
}
