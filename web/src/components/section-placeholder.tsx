import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type SectionPlaceholderProps = {
  title: string;
  description: string;
};

export function SectionPlaceholder({ title, description }: SectionPlaceholderProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          Task 8 skeleton complete. Entity-specific list/detail/forms will be implemented in Task 9.
        </p>
      </CardContent>
    </Card>
  );
}