"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/ModeToggle";
import { Home, History, Code2, GithubIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Header() {
  const pathname = usePathname();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-border/40 bg-background/60 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center space-x-2 group">
          <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
            <Code2 className="h-5 w-5 text-primary" />
          </div>
          <span className="font-bold text-lg tracking-tight">Manim Generator</span>
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          <Link
            href="/"
            className={cn(
              "px-4 py-2 rounded-full text-sm font-medium transition-all duration-200",
              pathname === "/"
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            )}
          >
            Home
          </Link>
          <Link
            href="/history"
            className={cn(
              "px-4 py-2 rounded-full text-sm font-medium transition-all duration-200",
              pathname === "/history"
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            )}
          >
            History
          </Link>
        </nav>

        <div className="flex items-center space-x-2">
          <div className="md:hidden flex space-x-1">
            <Button variant="ghost" size="icon" asChild className="rounded-full">
              <Link href="/">
                <Home className="h-5 w-5" />
              </Link>
            </Button>
            <Button variant="ghost" size="icon" asChild className="rounded-full">
              <Link href="/history">
                <History className="h-5 w-5" />
              </Link>
            </Button>
          </div>

          <Button variant="ghost" size="sm" asChild className="hidden sm:flex rounded-full gap-2 text-muted-foreground hover:text-foreground">
            <Link
              href="https://github.com/JagjeevanAK/manim-generator-studio"
              target="_blank"
              rel="noopener noreferrer"
            >
              <GithubIcon className="h-4 w-4" />
              <span>Star on GitHub</span>
            </Link>
          </Button>

          <div className="pl-2 border-l border-border/50 ml-2">
            <ModeToggle />
          </div>
        </div>
      </div>
    </header>
  );
}
