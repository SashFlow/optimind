"use client";
import {
  RoomAudioRenderer,
  useRoomContext,
  useVoiceAssistant,
} from "@livekit/components-react";
import { AnimatePresence, motion } from "framer-motion";
import { Room } from "livekit-client";
import { useEffect, useState } from "react";
import { AgentVisualizer } from "@/components/player/AgentVisualizer";
import { ControlBar } from "@/components/player/ControlBar";
import { MapContainer } from "@/components/player/MapContainer";
import { CabContainer } from "@/components/player/CabContainer";
import { RiMap2Line } from "@remixicon/react";
import { RiTaxiLine } from "@remixicon/react";

function SimpleVoiceAssistant(props: {
  onConnectButtonClicked: () => void;
  room: Room;
}) {
  const room = useRoomContext();
  const { state: agentState } = useVoiceAssistant();
  const [showCab, setShowCab] = useState(false);
  const [showMap, setShowMap] = useState(false);
  useEffect(() => {
    if (!room) return;

    // Register RPC method to receive flash cards
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handleShowFlashCard = async (data: any): Promise<string> => {
      try {
        console.log("Received flashcard RPC data:", data);

        // Check for the correct property in the RPC data
        if (!data || data.payload === undefined) {
          console.error("Invalid RPC data received:", data);
          return "Error: Invalid RPC data format";
        }

        console.log("Parsing payload:", data.payload);

        // Parse the payload string into a JSON object
        const payload =
          typeof data.payload === "string"
            ? JSON.parse(data.payload)
            : data.payload;

        if (payload.action === "cab") {
          setShowCab(true);
        } else if (payload.action === "map") {
          setShowMap(true);
        }

        return "Success";
      } catch (error) {
        console.error("Error processing flash card data:", error);
        return (
          "Error: " + (error instanceof Error ? error.message : String(error))
        );
      }
    };

    room.localParticipant.registerRpcMethod(
      "client.flashcard",
      handleShowFlashCard,
    );

    return () => {
      // Clean up RPC method when component unmounts
      room.localParticipant.unregisterRpcMethod("client.flashcard");
    };
  }, [room]);
  return (
    <>
      <AnimatePresence mode="wait">
        {agentState === "disconnected" ? (
          <motion.div
            key="disconnected"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3, ease: [0.09, 1.04, 0.245, 1.055] }}
            className="grid items-center justify-center h-full gap-4"
          >
            <div className="flex-1 w-full">
              <CabContainer show={showCab} onClose={() => setShowCab(false)} />
            </div>
            <div className="flex-1 w-full">
              <MapContainer show={showMap} onClose={() => setShowMap(false)} />
            </div>
            <iframe
              width="560"
              height="315"
              src="https://www.youtube.com/embed/t3jFuHdjMHU?rel=0&amp;controls=0&amp&amp;showinfo=0&amp;modestbranding=1&autoplay=1&loop=1&mute=1"
              frameBorder="0"
            ></iframe>
            <div className="flex justify-center items-center gap-4">
              <motion.button
                onClick={() => setShowMap(true)}
                className="bg-white text-black rounded-md px-2 py-1"
              >
                <RiMap2Line size={24} />
              </motion.button>
              <motion.button
                initial={{ scale: 0.95 }}
                animate={{ scale: 1 }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  repeatType: "reverse",
                }}
                className="uppercase px-4 py-2 bg-red-500 text-white rounded-md"
                onClick={() => props.onConnectButtonClicked()}
              >
                Chat With Your LDA Guide!
              </motion.button>
              <motion.button
                onClick={() => setShowCab(true)}
                className="bg-white text-black rounded-md px-2 py-1"
              >
                <RiTaxiLine size={24} />
              </motion.button>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="connected"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3, ease: [0.09, 1.04, 0.245, 1.055] }}
            className="flex flex-col items-center gap-4 h-full"
          >
            <AgentVisualizer />
            <div className="flex-1 w-full">
              <CabContainer show={showCab} onClose={() => setShowCab(false)} />
            </div>
            <div className="flex-1 w-full">
              <MapContainer show={showMap} onClose={() => setShowMap(false)} />
            </div>
            <div className="w-full">
              <ControlBar
                onConnectButtonClicked={props.onConnectButtonClicked}
                setShowCab={() => setShowCab(!showCab)}
                setShowMap={() => setShowMap(!showMap)}
              />
            </div>
            <RoomAudioRenderer />
            {/* <NoAgentNotification state={agentState} /> */}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
