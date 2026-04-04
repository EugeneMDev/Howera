export type FeedbackTone = "danger" | "info" | "success" | "warning";

export interface FeedbackMessage {
  description: string;
  title: string;
  tone: FeedbackTone;
}
