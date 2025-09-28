"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useEditorStore } from "../../state/editorStore";
import { Button } from "../ui/Button";

const metaSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  tags: z.string().optional(),
  version: z.string().optional()
});

export type MetaFormValues = z.infer<typeof metaSchema>;

export const MetaPanel = () => {
  const metadata = useEditorStore((state) => state.metadata);
  const setMetadata = useEditorStore((state) => state.setMetadata);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors }
  } = useForm<MetaFormValues>({
    resolver: zodResolver(metaSchema),
    defaultValues: {
      title: metadata.title ?? "",
      description: metadata.description ?? "",
      tags: metadata.tags?.join(", ") ?? "",
      version: metadata.version ? String(metadata.version) : ""
    }
  });

  useEffect(() => {
    reset({
      title: metadata.title ?? "",
      description: metadata.description ?? "",
      tags: metadata.tags?.join(", ") ?? "",
      version: metadata.version ? String(metadata.version) : ""
    });
  }, [metadata, reset]);

  const onSubmit = (values: MetaFormValues) => {
    const tags = values.tags
      ? values.tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean)
      : [];
    const version = values.version ? Number.parseInt(values.version, 10) : undefined;
    setMetadata({
      title: values.title,
      description: values.description,
      tags,
      version
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
      <div>
        <label className="text-sm font-medium">Title</label>
        <input
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="Rulepack title"
          {...register("title")}
        />
        {errors.title ? <p className="text-xs text-destructive">{errors.title.message}</p> : null}
      </div>
      <div>
        <label className="text-sm font-medium">Description</label>
        <textarea
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          rows={3}
          placeholder="Summary of the rulepack"
          {...register("description")}
        />
      </div>
      <div>
        <label className="text-sm font-medium">Tags</label>
        <input
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="Comma separated tags"
          {...register("tags")}
        />
      </div>
      <div>
        <label className="text-sm font-medium">Version</label>
        <input
          type="number"
          min={1}
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="1"
          {...register("version")}
        />
      </div>
      <Button type="submit" variant="secondary" className="w-full">
        Update metadata
      </Button>
    </form>
  );
};
