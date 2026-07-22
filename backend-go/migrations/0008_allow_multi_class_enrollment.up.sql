-- 0008: Allow a student to enroll in multiple classes.
-- Previously uq_class_enrollment_student enforced one class per student.
-- This migration drops that constraint so a student may join several classes.

ALTER TABLE public.class_enrollments DROP CONSTRAINT IF EXISTS uq_class_enrollment_student;
