import { useVoiceAssistant } from "@livekit/components-react";
import { RiMap2Line, RiTaxiLine } from "@remixicon/react";
import { AnimatePresence, motion } from "framer-motion";
import { Button } from "../ui/button";
import { VoiceAssistantControlBar } from "@livekit/components-react";
import { DisconnectButton } from "@livekit/components-react";
import { CloseIcon } from "../CloseIcon";

export function ControlBar(props: {
  onConnectButtonClicked: () => void;
  setShowCab: (show: boolean) => void;
  setShowMap: (show: boolean) => void;
}) {
  const { state: agentState } = useVoiceAssistant();

  return (
    <div className="relative h-[60px]">
      <AnimatePresence>
        {agentState === "disconnected" && (
          <div className="uppercase absolute left-1/2 -translate-x-1/2 flex gap-2">
            <motion.button
              onClick={() => props.setShowMap(true)}
              className="bg-white text-black rounded-md px-2 py-1"
            >
              <RiMap2Line size={24} />
            </motion.button>
            <motion.button
              initial={{ opacity: 0, top: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, top: "-10px" }}
              transition={{ duration: 1, ease: [0.09, 1.04, 0.245, 1.055] }}
              onClick={() => props.onConnectButtonClicked()}
              className="px-4 py-2 bg-white text-black rounded-md"
            >
              Connect to Agent
            </motion.button>
            <motion.button
              onClick={() => props.setShowCab(true)}
              className="bg-white text-black rounded-md px-2 py-1"
            >
              <RiTaxiLine size={24} />
            </motion.button>
          </div>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {agentState !== "disconnected" && agentState !== "connecting" && (
          <motion.div
            initial={{ opacity: 0, top: "10px" }}
            animate={{ opacity: 1, top: 0 }}
            exit={{ opacity: 0, top: "-10px" }}
            transition={{ duration: 0.4, ease: [0.09, 1.04, 0.245, 1.055] }}
            className="flex h-8 absolute left-1/2 -translate-x-1/2  justify-center gap-2"
          >
            <Button
              onClick={() => props.setShowMap(true)}
              variant="ghost"
              size="icon"
              className="bg-white text-black rounded-md px-2 py-1"
            >
              <RiMap2Line size={24} />
            </Button>
            <VoiceAssistantControlBar controls={{ leave: false }} />
            <DisconnectButton>
              <CloseIcon />
            </DisconnectButton>
            <Button
              onClick={() => props.setShowCab(true)}
              variant="ghost"
              size="icon"
              className="bg-white text-black rounded-md px-2 py-1"
            >
              <RiTaxiLine size={24} />
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
