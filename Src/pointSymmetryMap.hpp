

#ifndef pointSymmetryMap_hpp
#define pointSymmetryMap_hpp

#include <stdio.h>
#include <vector>

#include <lx_item.hpp>
#include <lx_mesh.hpp>
#include <lx_log.hpp>

/*
 * Point Symmetry Map
 * Builds a map of vertices symmetrical along X axis for a given mesh.
 * The map can then be queried for symmetrical vertices.
 */

static const int emptyMapElement = -1;

class PointSymmetryMap
{
public:
    PointSymmetryMap() {};
    ~PointSymmetryMap() {};
    
    bool build(CLxUser_Mesh &mesh);
    bool getSymmetricPointIndex(unsigned int index, unsigned int *symmetricIndex);
    
private:    
    bool _findClosestSymmetricPoint(CLxUser_Point &point, CLxUser_Polygon &polygon, LXtPointID &symmetricPointID);
    
    std::vector<int> _symmap;

};

#endif /* pointSymmetryMap_hpp */
