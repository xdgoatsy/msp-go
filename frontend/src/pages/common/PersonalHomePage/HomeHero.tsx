import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { Play } from 'lucide-react';
import calculusVisualLight from '@/assets/personal-home-calculus-light.webp';
import calculusVisualDark from '@/assets/personal-home-calculus-dark.webp';
import { getGreeting } from './homeData';
import type { HomeRole } from './types';

interface HomeHeroProps {
  role: HomeRole;
  name: string;
  primaryHref: string;
  primaryLabel: string;
  primaryContext: string;
}

export function HomeHero({
  role,
  name,
  primaryHref,
  primaryLabel,
  primaryContext,
}: HomeHeroProps) {
  const shouldReduceMotion = useReducedMotion();
  const greeting = getGreeting(new Date().getHours());
  const roleCopy = role === 'teacher'
    ? '把复杂的学习数据，整理成今天清晰的教学判断。'
    : '坚持每天进步一点点，数学思维终将成就你的无限可能。';

  return (
    <section className="overflow-hidden border-b border-surface-100 bg-white dark:border-surface-800 dark:bg-[#01020a]">
      <div className="mx-auto grid min-h-[300px] max-w-7xl items-center gap-4 px-4 py-8 sm:px-6 lg:grid-cols-[0.88fr_1.12fr] lg:px-8 lg:py-5">
        <motion.div
          initial={shouldReduceMotion ? false : { opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: shouldReduceMotion ? 0 : 0.45, ease: [0, 0, 0.2, 1] }}
          className="relative z-10 py-4 lg:py-8"
        >
          <h1 className="max-w-xl text-4xl font-bold leading-tight text-surface-950 [overflow-wrap:anywhere] sm:text-5xl dark:text-white">
            {greeting}，{name}
          </h1>
          <p className="mt-4 max-w-lg text-base leading-7 text-surface-500 dark:text-surface-400">
            {roleCopy}
          </p>

          <div className="mt-8 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
            <motion.div
              whileHover={shouldReduceMotion ? undefined : { y: -2 }}
              whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
            >
              <Link
                to={primaryHref}
                className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-primary-700 px-7 text-sm font-semibold text-white shadow-lg shadow-primary-700/20 transition-colors hover:bg-primary-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-primary-400 dark:focus-visible:ring-offset-surface-950"
              >
                <Play className="h-4 w-4 fill-current" aria-hidden="true" />
                {primaryLabel}
              </Link>
            </motion.div>
            <p className="max-w-sm text-sm leading-6 text-surface-500 [overflow-wrap:anywhere] dark:text-surface-400">
              {primaryContext}
            </p>
          </div>
        </motion.div>

        <motion.figure
          initial={shouldReduceMotion ? false : { opacity: 0, x: 24 }}
          animate={shouldReduceMotion ? { opacity: 1, x: 0 } : { opacity: 1, x: 0, y: [0, -6, 0] }}
          transition={shouldReduceMotion
            ? { duration: 0 }
            : {
                opacity: { duration: 0.55, delay: 0.08 },
                x: { duration: 0.55, delay: 0.08, ease: [0, 0, 0.2, 1] },
                y: { duration: 7, repeat: Infinity, ease: 'easeInOut', delay: 0.6 },
              }}
          className="relative -mx-4 min-h-[230px] overflow-hidden sm:mx-0 sm:min-h-[280px] lg:min-h-[340px]"
        >
          <img
            src={calculusVisualLight}
            alt="蓝紫色微积分曲面、展开的数学笔记本与钢笔"
            className="absolute inset-0 h-full w-full origin-right scale-[1.15] object-cover object-center sm:scale-125 lg:scale-105 lg:object-contain lg:object-right dark:hidden"
          />
          <img
            src={calculusVisualDark}
            alt="深色背景中的蓝紫色微积分曲面、数学笔记本与钢笔"
            className="absolute inset-0 hidden h-full w-full origin-right scale-[1.15] object-cover object-center sm:scale-125 lg:scale-105 lg:object-contain lg:object-right dark:block"
          />
        </motion.figure>
      </div>
    </section>
  );
}
