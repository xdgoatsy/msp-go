import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/Button';
import { Card, CardContent } from '../../components/ui/Card';
import { ArrowLeft, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '../../libs/utils/cn';

interface FAQItem {
  question: string;
  answer: string;
}

const faqData: FAQItem[] = [
  {
    question: '如何注册账号？',
    answer: '点击首页的「注册」按钮，使用学号进行注册。填写必要的个人信息后，即可完成注册。首次登录后建议完善个人资料。',
  },
  {
    question: '忘记密码怎么办？',
    answer: '在登录页面点击「忘记密码」，提交密码重置申请并等待管理员审批。审批通过后，管理员会通过线下安全渠道告知临时密码。',
  },
  {
    question: 'AI 助手支持哪些功能？',
    answer: 'AI 助手支持解答数学问题、讲解概念、分析错题、规划学习路径等功能。你可以上传题目图片或直接输入数学公式进行提问。',
  },
  {
    question: '如何输入数学公式？',
    answer: '平台支持 LaTeX 格式的数学公式输入。例如输入 $x^2$ 显示 x 的平方，输入 $\\frac{a}{b}$ 显示分数。在输入框中可以使用公式编辑器辅助输入。',
  },
  {
    question: '错题本的题目从哪里来？',
    answer: '错题本会自动收集你在智能刷题、测验等模块中做错的题目。你也可以手动将题目添加到错题本中进行重点复习。',
  },
  {
    question: '学习数据会被保存多久？',
    answer: '你的学习数据会在账号有效期内持续保存。包括答题记录、学习会话、错题本等数据都会安全存储，方便你随时查看学习历史。',
  },
  {
    question: '可以在手机上使用吗？',
    answer: '平台支持响应式设计，可以在手机浏览器中正常使用。建议使用较新版本的 Chrome、Safari 或 Edge 浏览器以获得最佳体验。',
  },
  {
    question: '如何反馈问题或建议？',
    answer: '你可以通过「联系我们」页面提供的邮箱发送反馈，或在学习会话中直接向 AI 助手反馈使用问题。我们会认真对待每一条反馈。',
  },
];

const FAQItemComponent: React.FC<{ item: FAQItem }> = ({ item }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border-b border-surface-200 dark:border-surface-700 last:border-b-0">
      <button
        className="w-full py-4 flex items-center justify-between text-left hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors px-4 -mx-4"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="font-medium text-surface-900 dark:text-surface-100 pr-4">
          {item.question}
        </span>
        {isOpen ? (
          <ChevronUp className="w-5 h-5 text-surface-400 shrink-0" />
        ) : (
          <ChevronDown className="w-5 h-5 text-surface-400 shrink-0" />
        )}
      </button>
      <div
        className={cn(
          'overflow-hidden transition-all duration-200',
          isOpen ? 'max-h-96 pb-4' : 'max-h-0'
        )}
      >
        <p className="text-sm text-surface-600 dark:text-surface-400 leading-relaxed">
          {item.answer}
        </p>
      </div>
    </div>
  );
};

export const FAQPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-950 text-surface-900 dark:text-surface-100">
      <div className="container mx-auto px-6 py-8 max-w-3xl">
        <Button
          variant="ghost"
          className="mb-6 pl-0 hover:bg-transparent hover:text-primary-600 dark:hover:text-primary-400"
          onClick={() => navigate('/')}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          返回主界面
        </Button>

        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-surface-900 dark:text-surface-100">
            常见问题
          </h1>
          <p className="mt-3 text-surface-500 dark:text-surface-400">
            查找常见问题的解答，快速解决你的疑惑
          </p>
        </div>

        <Card>
          <CardContent className="p-6">
            <div className="divide-y divide-surface-200 dark:divide-surface-700">
              {faqData.map((item, index) => (
                <FAQItemComponent key={index} item={item} />
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="mt-8 text-center text-sm text-surface-500 dark:text-surface-400">
          <p>没有找到你的问题？</p>
          <Button
            variant="link"
            className="text-primary-600 dark:text-primary-400"
            onClick={() => navigate('/contact')}
          >
            联系我们
          </Button>
        </div>
      </div>
    </div>
  );
};
