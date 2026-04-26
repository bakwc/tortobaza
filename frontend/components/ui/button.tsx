import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]/40",
  {
    variants: {
      variant: {
        primary:
          "bg-[var(--brand)] text-[var(--brand-foreground)] hover:bg-[var(--brand)]/90",
        price:
          "bg-[var(--price)] text-white hover:bg-[var(--price)]/90 tracking-wide",
        outline:
          "border border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream)]",
        ghost: "text-[var(--ink)] hover:bg-[var(--cream)]",
        soft: "bg-white text-[var(--ink)] border border-[var(--line)] hover:bg-[var(--cream)]",
      },
      size: {
        sm: "h-9 px-4 text-sm rounded-full",
        md: "h-11 px-6 text-sm rounded-full",
        lg: "h-12 px-8 text-base rounded-full",
        icon: "h-10 w-10 rounded-full",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { buttonVariants };
