import { InstructionEditorScreen } from "@/features/instructions/components/instruction-editor-screen";

interface InstructionDetailPageProps {
  params: Promise<{ instructionId: string }>;
}

export default async function InstructionDetailPage({ params }: InstructionDetailPageProps) {
  const { instructionId } = await params;

  return <InstructionEditorScreen instructionId={instructionId} />;
}
