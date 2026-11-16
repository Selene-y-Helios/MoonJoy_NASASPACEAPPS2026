import type { SpaceSnapshot } from '../types';
// Illustrative positions for the original interface; not JPL ephemerides.
export const demoSnapshot:SpaceSnapshot = {
  timestampUTC:'2026-11-14T18:00:00.000Z',frame:'MOON_ME',
  earthFromMoonKm:[310000,70000,210000],sunFromMoonKm:[-100000000,45000000,88000000],
  source:'DEMO DATA · not JPL ephemerides',status:'demo',
  sites:[
    {id:'shackleton',name:'Shackleton Rim',latitudeDeg:-89.7,longitudeDeg:0,description:'Illustrative point near Shackleton crater. Test coordinates.',tag:'SOUTH POLE'},
    {id:'malapert',name:'Malapert Region',latitudeDeg:-85.9,longitudeDeg:0,description:'Illustrative point near Malapert. Test coordinates.',tag:'ELEVATION'},
    {id:'degerlache',name:'de Gerlache Region',latitudeDeg:-88.5,longitudeDeg:-90,description:'Illustrative point near de Gerlache. Test coordinates.',tag:'CRATER'},
  ]
};
