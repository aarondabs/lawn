import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-2xl py-8">
      <Card>
        <CardHeader>
          <CardTitle>Page not found</CardTitle>
          <CardDescription>
            The route you requested does not exist in the Task 8 application shell.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            Return to the dashboard and continue from the main navigation.
          </p>
          <Link href="/" className={buttonVariants({ variant: "secondary" })}>
            Back to dashboard
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}