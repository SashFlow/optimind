import { useRoomContext } from "@livekit/components-react";
import { Room } from "livekit-client";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AgentVisualizer } from "./AgentVisualizer";
import { CabContainer } from "./CabContainer";
import { MapContainer } from "./MapContainer";
import { ControlBar } from "./ControlBar";
import { RoomAudioRenderer } from "@livekit/components-react";
// import { NoAgentNotification } from "@/components/NoAgentNotification";

export function Assistant(props: {
  onConnectButtonClicked: () => void;
  room: Room;
}) {
  const room = useRoomContext();
  // const { state: agentState } = useVoiceAssistant();
  const [showCab, setShowCab] = useState(false);
  const [showMap, setShowMap] = useState(false);
  useEffect(() => {
    props.onConnectButtonClicked();
  }, []);

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
      handleShowFlashCard
    );

    return () => {
      // Clean up RPC method when component unmounts
      room.localParticipant.unregisterRpcMethod("client.flashcard");
    };
  }, [room]);
  return (
    <>
      <AnimatePresence mode="wait">
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
      </AnimatePresence>
    </>
  );
}
