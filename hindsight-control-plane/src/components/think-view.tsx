"use client";

import { useState } from "react";
import { client } from "@/lib/api";
import { useBank } from "@/lib/bank-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, Info, Tag, Clock, Database } from "lucide-react";
import JsonView from "react18-json-view";
import "react18-json-view/src/style.css";

type TagsMatch = "any" | "all" | "any_strict" | "all_strict";
type ViewMode = "answer" | "trace" | "json";

export function ThinkView() {
  const { currentBank } = useBank();
  const [query, setQuery] = useState("");
  const [budget, setBudget] = useState<"low" | "mid" | "high">("mid");
  const [maxTokens, setMaxTokens] = useState<number>(4096);
  const [includeFacts, setIncludeFacts] = useState(true);
  const [includeToolCalls, setIncludeToolCalls] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>("answer");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [tags, setTags] = useState("");
  const [tagsMatch, setTagsMatch] = useState<TagsMatch>("any");

  const runReflect = async () => {
    if (!currentBank || !query) return;

    setLoading(true);
    setViewMode("answer");
    try {
      // Parse tags from comma-separated string
      const parsedTags = tags
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      const data: any = await client.reflect({
        bank_id: currentBank,
        query,
        budget,
        max_tokens: maxTokens,
        include_facts: includeFacts,
        include_tool_calls: includeToolCalls,
        ...(parsedTags.length > 0 && { tags: parsedTags, tags_match: tagsMatch }),
      });
      setResult(data);
    } catch (error) {
      console.error("Error running reflect:", error);
      alert("Error running reflect: " + (error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (!currentBank) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center py-16">
          <Database className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-xl font-semibold mb-2">No Bank Selected</h3>
          <p className="text-muted-foreground">Select a memory bank to start reflecting.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Query Input */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Sparkles className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What would you like to reflect on?"
                className="pl-10 h-12 text-lg"
                onKeyDown={(e) => e.key === "Enter" && runReflect()}
              />
            </div>
            <Button onClick={runReflect} disabled={loading || !query} className="h-12 px-8">
              {loading ? "Reflecting..." : "Reflect"}
            </Button>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-6 mt-4 pt-4 border-t">
            {/* Budget */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">Budget:</span>
              <Select value={budget} onValueChange={(value: any) => setBudget(value)}>
                <SelectTrigger className="w-24 h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="mid">Mid</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Max Tokens */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Tokens:</span>
              <Input
                type="number"
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value) || 4096)}
                className="w-24 h-8"
              />
            </div>

            <div className="h-6 w-px bg-border" />

            {/* Include options */}
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <Checkbox
                  checked={includeFacts}
                  onCheckedChange={(c) => setIncludeFacts(c as boolean)}
                />
                <span className="text-sm">Include Facts</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <Checkbox
                  checked={includeToolCalls}
                  onCheckedChange={(c) => setIncludeToolCalls(c as boolean)}
                />
                <span className="text-sm">Include Tools</span>
              </label>
            </div>
          </div>

          {/* Tags Filter */}
          <div className="flex items-center gap-4 mt-4 pt-4 border-t">
            <Tag className="h-4 w-4 text-muted-foreground" />
            <div className="flex-1 max-w-md">
              <Input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="Filter by tags (comma-separated)"
                className="h-8"
              />
            </div>
            <Select value={tagsMatch} onValueChange={(v) => setTagsMatch(v as TagsMatch)}>
              <SelectTrigger className="w-40 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Any (incl. untagged)</SelectItem>
                <SelectItem value="all">All (incl. untagged)</SelectItem>
                <SelectItem value="any_strict">Any (strict)</SelectItem>
                <SelectItem value="all_strict">All (strict)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Loading State */}
      {loading && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4" />
            <p className="text-muted-foreground">Reflecting on memories...</p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {!loading && result && (
        <div className="space-y-4">
          {/* Summary Stats & Tabs */}
          <div className="flex items-center gap-6 text-sm">
            {result.usage && (
              <>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Input tokens:</span>
                  <span className="font-semibold">
                    {result.usage.input_tokens?.toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Output tokens:</span>
                  <span className="font-semibold">
                    {result.usage.output_tokens?.toLocaleString()}
                  </span>
                </div>
              </>
            )}
            {result.tool_calls && (
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Tool calls:</span>
                <span className="font-semibold">{result.tool_calls.length}</span>
                <span className="text-muted-foreground">
                  ({result.tool_calls.reduce((sum: number, tc: any) => sum + tc.duration_ms, 0)}ms)
                </span>
              </div>
            )}
            {result.llm_calls && (
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">LLM calls:</span>
                <span className="font-semibold">{result.llm_calls.length}</span>
                <span className="text-muted-foreground">
                  ({result.llm_calls.reduce((sum: number, lc: any) => sum + lc.duration_ms, 0)}ms)
                </span>
              </div>
            )}

            <div className="flex-1" />

            {/* View Mode Tabs */}
            <div className="flex gap-1 bg-muted p-1 rounded-lg">
              {(["answer", "trace", "json"] as ViewMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    viewMode === mode
                      ? "bg-background shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {mode === "answer" ? "Answer" : mode === "trace" ? "Trace" : "JSON"}
                </button>
              ))}
            </div>
          </div>

          {/* Answer View */}
          {viewMode === "answer" && (
            <div className="space-y-6">
              {/* Main Answer */}
              <Card>
                <CardHeader>
                  <CardTitle>Answer</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-base leading-relaxed whitespace-pre-wrap">{result.text}</div>
                </CardContent>
              </Card>

              {/* New Opinions Formed */}
              {result.new_opinions && result.new_opinions.length > 0 && (
                <Card className="border-green-200 dark:border-green-800">
                  <CardHeader className="bg-green-50 dark:bg-green-950">
                    <CardTitle className="flex items-center gap-2">
                      <Sparkles className="w-5 h-5" />
                      New Opinions Formed
                    </CardTitle>
                    <CardDescription>New beliefs generated from this interaction</CardDescription>
                  </CardHeader>
                  <CardContent className="pt-6">
                    <div className="space-y-3">
                      {result.new_opinions.map((opinion: any, i: number) => (
                        <div key={i} className="p-3 bg-muted rounded-lg border border-border">
                          <div className="font-semibold text-foreground">{opinion.text}</div>
                          <div className="text-sm text-muted-foreground mt-1">
                            Confidence: {opinion.confidence?.toFixed(2)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Trace View - Split Layout */}
          {viewMode === "trace" && (
            <div className="space-y-4">
              {/* LLM Calls Summary */}
              {result.llm_calls && result.llm_calls.length > 0 && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">LLM Calls</CardTitle>
                    <CardDescription className="text-xs">
                      {result.llm_calls.length} LLM call{result.llm_calls.length !== 1 ? "s" : ""} •{" "}
                      {result.llm_calls.reduce((sum: number, lc: any) => sum + lc.duration_ms, 0)}ms
                      total
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {result.llm_calls.map((lc: any, i: number) => (
                        <div
                          key={i}
                          className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-lg border border-border"
                        >
                          <span className="text-sm font-medium">{lc.scope}</span>
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {lc.duration_ms}ms
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Tool Calls and Based On - Side by Side */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Left: Tool Calls */}
                <Card className="h-fit">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Tool Calls</CardTitle>
                    <CardDescription className="text-xs">
                      {result.tool_calls?.length || 0} tool call
                      {result.tool_calls?.length !== 1 ? "s" : ""} executed
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {!includeToolCalls ? (
                      <div className="flex items-start gap-3 p-3 bg-muted border border-border rounded-lg">
                        <Info className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="font-medium text-sm text-foreground">Not included</p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            Enable "Include Tool Calls" to see trace.
                          </p>
                        </div>
                      </div>
                    ) : result.tool_calls && result.tool_calls.length > 0 ? (
                      <div className="space-y-3 max-h-[500px] overflow-y-auto">
                        {result.tool_calls.map((tc: any, i: number) => (
                          <div key={i} className="border border-border rounded-lg overflow-hidden">
                            <div className="flex items-center justify-between px-3 py-1.5 bg-muted/50">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-mono text-muted-foreground">
                                  #{i + 1}
                                </span>
                                <span className="font-medium text-sm text-foreground">
                                  {tc.tool}
                                </span>
                              </div>
                              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                <Clock className="w-3 h-3" />
                                {tc.duration_ms}ms
                              </div>
                            </div>
                            <div className="p-2 space-y-2">
                              <div>
                                <p className="text-[10px] font-semibold text-muted-foreground mb-1">
                                  Input:
                                </p>
                                <div className="bg-muted p-1.5 rounded text-xs overflow-auto max-h-32">
                                  <JsonView src={tc.input} collapsed={1} theme="default" />
                                </div>
                              </div>
                              {tc.output && (
                                <div>
                                  <p className="text-[10px] font-semibold text-muted-foreground mb-1">
                                    Output:
                                  </p>
                                  <div className="bg-muted p-1.5 rounded text-xs overflow-auto max-h-32">
                                    <JsonView src={tc.output} collapsed={1} theme="default" />
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex items-start gap-3 p-3 bg-muted border border-border rounded-lg">
                        <Info className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="font-medium text-sm text-foreground">No tool calls</p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            No tools were called during this reflection.
                          </p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Right: Based On Facts */}
                <Card className="h-fit">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Based On</CardTitle>
                    <CardDescription className="text-xs">
                      {result.based_on?.length || 0} memories used
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {!includeFacts ? (
                      <div className="flex items-start gap-3 p-3 bg-muted border border-border rounded-lg">
                        <Info className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="font-medium text-sm text-foreground">Not included</p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            Enable "Include Facts" to see memories.
                          </p>
                        </div>
                      </div>
                    ) : result.based_on && result.based_on.length > 0 ? (
                      <div className="space-y-4 max-h-[500px] overflow-y-auto">
                        {(() => {
                          const worldFacts = result.based_on.filter((f: any) => f.type === "world");
                          const experienceFacts = result.based_on.filter(
                            (f: any) => f.type === "experience"
                          );
                          const opinionFacts = result.based_on.filter(
                            (f: any) => f.type === "opinion"
                          );
                          const mentalModelFacts = result.based_on.filter(
                            (f: any) => f.type === "mental_model"
                          );

                          return (
                            <>
                              {/* Mental Models */}
                              {mentalModelFacts.length > 0 && (
                                <div className="space-y-1.5">
                                  <div className="flex items-center gap-2 text-xs font-semibold text-orange-600 dark:text-orange-400">
                                    <div className="w-2 h-2 rounded-full bg-orange-500" />
                                    Mental Models ({mentalModelFacts.length})
                                  </div>
                                  <div className="space-y-1.5">
                                    {mentalModelFacts.map((fact: any, i: number) => (
                                      <div key={i} className="p-2 bg-muted rounded text-xs">
                                        {fact.text}
                                        {fact.context && (
                                          <div className="text-[10px] text-muted-foreground mt-1">
                                            {fact.context}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* World Facts */}
                              {worldFacts.length > 0 && (
                                <div className="space-y-1.5">
                                  <div className="flex items-center gap-2 text-xs font-semibold text-blue-600 dark:text-blue-400">
                                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                                    World ({worldFacts.length})
                                  </div>
                                  <div className="space-y-1.5">
                                    {worldFacts.map((fact: any, i: number) => (
                                      <div key={i} className="p-2 bg-muted rounded text-xs">
                                        {fact.text}
                                        {fact.context && (
                                          <div className="text-[10px] text-muted-foreground mt-1">
                                            {fact.context}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Experience Facts */}
                              {experienceFacts.length > 0 && (
                                <div className="space-y-1.5">
                                  <div className="flex items-center gap-2 text-xs font-semibold text-green-600 dark:text-green-400">
                                    <div className="w-2 h-2 rounded-full bg-green-500" />
                                    Experience ({experienceFacts.length})
                                  </div>
                                  <div className="space-y-1.5">
                                    {experienceFacts.map((fact: any, i: number) => (
                                      <div key={i} className="p-2 bg-muted rounded text-xs">
                                        {fact.text}
                                        {fact.context && (
                                          <div className="text-[10px] text-muted-foreground mt-1">
                                            {fact.context}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Opinion Facts */}
                              {opinionFacts.length > 0 && (
                                <div className="space-y-1.5">
                                  <div className="flex items-center gap-2 text-xs font-semibold text-purple-600 dark:text-purple-400">
                                    <div className="w-2 h-2 rounded-full bg-purple-500" />
                                    Opinions ({opinionFacts.length})
                                  </div>
                                  <div className="space-y-1.5">
                                    {opinionFacts.map((fact: any, i: number) => (
                                      <div key={i} className="p-2 bg-muted rounded text-xs">
                                        {fact.text}
                                        {fact.context && (
                                          <div className="text-[10px] text-muted-foreground mt-1">
                                            {fact.context}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </>
                          );
                        })()}
                      </div>
                    ) : (
                      <div className="flex items-start gap-3 p-3 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg">
                        <Info className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="font-medium text-sm text-amber-900 dark:text-amber-100">
                            No facts found
                          </p>
                          <p className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">
                            No memories were used to generate this answer.
                          </p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {/* JSON View */}
          {viewMode === "json" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Raw Response</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-muted p-4 rounded-lg overflow-auto max-h-[600px]">
                  <JsonView src={result} collapsed={2} theme="default" />
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Empty State */}
      {!loading && !result && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Sparkles className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Ready to Reflect</h3>
            <p className="text-muted-foreground text-center max-w-md">
              Enter a question above to query the memory bank and generate a disposition-aware
              response.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
