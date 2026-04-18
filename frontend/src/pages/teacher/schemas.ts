import { z } from 'zod';

export const classCreationSchema = z.object({
  name: z
    .string()
    .min(2, '班级名称至少 2 个字符')
    .max(200, '班级名称最多 200 个字符'),
  description: z.string().max(500, '班级描述最多 500 个字符').optional().or(z.literal('')),
});

export type ClassCreationFormData = z.infer<typeof classCreationSchema>;
