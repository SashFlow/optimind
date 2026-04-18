import { Button } from "@/components/ui/button";
import { RiClipboardLine } from "@remixicon/react";

export const CopyButton = (props: { text: string }) => {
  const handleCopy = () => {
    navigator.clipboard.writeText(props.text);
  };
  return (
    <Button onClick={handleCopy} variant="ghost" size="icon">
      <RiClipboardLine size={24} />
    </Button>
  );
};
