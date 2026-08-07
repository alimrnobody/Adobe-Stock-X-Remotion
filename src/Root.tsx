import React from 'react';
import { Composition } from 'remotion';
import { NeonCrimsonNetwork } from './NeonCrimsonNetwork';
import { NeonRedGrid } from './NeonRedGrid';
import { NeonScarletWeb } from './NeonScarletWeb';
import { NeonOrangeCircuit } from './NeonOrangeCircuit';
import { NeonTangerineMesh } from './NeonTangerineMesh';
import { NeonAmberConstellation } from './NeonAmberConstellation';
import { NeonGoldNodes } from './NeonGoldNodes';
import { NeonYellowSignal } from './NeonYellowSignal';
import { NeonLimeMatrix } from './NeonLimeMatrix';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="NeonCrimsonNetwork"
        component={NeonCrimsonNetwork}
        durationInFrames={480}
        fps={60}
        width={3840}
        height={2160}
      />
      <Composition
        id="NeonRedGrid"
        component={NeonRedGrid}
        durationInFrames={600}
        fps={60}
        width={3840}
        height={2160}
      />
      <Composition
        id="NeonScarletWeb"
        component={NeonScarletWeb}
        durationInFrames={480}
        fps={60}
        width={3840}
        height={2160}
      />
      <Composition
        id="NeonOrangeCircuit"
        component={NeonOrangeCircuit}
        durationInFrames={720}
        fps={60}
        width={3840}
        height={2160}
      />
      <Composition
        id="NeonTangerineMesh"
        component={NeonTangerineMesh}
        durationInFrames={600}
        fps={60}
        width={3840}
        height={2160}
      />
      <Composition
        id="NeonAmberConstellation"
        component={NeonAmberConstellation}
        durationInFrames={480}
        fps={60}
        width={3840}
        height={2160}
      />
      <Composition
        id="NeonGoldNodes"
        component={NeonGoldNodes}
        durationInFrames={480}
        fps={60}
        width={3840}
        height={2160}
      />
      <Composition
        id="NeonYellowSignal"
        component={NeonYellowSignal}
        durationInFrames={600}
        fps={60}
        width={3840}
        height={2160}
      />
      <Composition
        id="NeonLimeMatrix"
        component={NeonLimeMatrix}
        durationInFrames={480}
        fps={60}
        width={3840}
        height={2160}
      />
    </>
  );
};
