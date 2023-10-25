
#include <sstream>
#include <chrono>

#include "lxu_vector.hpp"

#include "pointSymmetryMap.hpp"

/*
 * Builds new symmetry map.
 *
 * Note that this works correctly ONLY if symmetry is turned on in MODO.
 * This is because MODO's symmetry SDK methods are dependend on the symmetry being on in UI.
 * The nice thing about that is that if you set symmetry to topology one
 * SDK will automatically use it!
 */

bool
PointSymmetryMap::build(CLxUser_Mesh &mesh)
{
	auto startTime = std::chrono::steady_clock::now();

    unsigned int pointsN = mesh.NPoints();
    
    // Initialise vector with empty map element values.
    _symmap.clear();
    _symmap.reserve(pointsN);
    for (int i = 0; i < pointsN; i++) { _symmap.push_back(emptyMapElement); }
    
    CLxUser_Point point;
    point.fromMesh(mesh);
    CLxUser_Polygon polygon;
    polygon.fromMesh(mesh);

    CLxUser_LogService logService;
    CLxUser_Log log;
    logService.GetSubSystem("riggingsys", log);
    
	unsigned int symmetryCount = 0;
	unsigned int closestCount = 0;
	unsigned int onCenterCount = 0;

    // Go through all mesh points here
    for ( unsigned int i = 0; i < pointsN; i++ )
    {
        point.SelectByIndex(i);
        LXtPointID symmetricPointID;
        
        // This point already has a symmetric value set.
        if (_symmap.at(i) != emptyMapElement) {
            continue;
        }
        
        // Axis vertices have no symmetry.
        if (point.OnSymmetryCenter() == LXe_TRUE)
        {
			onCenterCount++;
            continue;
        }
        else
        {
            bool result = false;
            if (point.Symmetry(&symmetricPointID) == LXe_OK) {
				symmetryCount++;
                result = true;
            }
            if (!result) {
                result = _findClosestSymmetricPoint(point, polygon, symmetricPointID);
				if (result)
				{
					closestCount++;
				}
            }
            
            if (result) {
                CLxUser_Point pointSymmetric;
                point.Spawn(pointSymmetric);
                pointSymmetric.Select(symmetricPointID);
                unsigned int symmetricPointIndex;
                pointSymmetric.Index(&symmetricPointIndex);
                _symmap.at(i) = symmetricPointIndex;
                // Set symmetry back on a symmetric point only if it's still empty
                // and does not have symmetric point assigned already.
                // This avoids bad cross assignments that would cause some points
                // to have wrong mirrored values.
                if (_symmap.at(symmetricPointIndex) == emptyMapElement) {
                    _symmap.at(symmetricPointIndex) = i;
                }
            }
        }

        // Debug output
        //std::stringstream ss;
        //ss << i << " - " << _symmap.at(i) << "  ";
        //std::string msg = ss.str();
        
        //log.Message(LXe_INFO, msg.c_str());
    }

	auto endTime = std::chrono::steady_clock::now();
	auto elapsedTime = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime).count();
	float elapsedTimeF = (float)(elapsedTime) / 1000.0;

	std::stringstream ss;
	ss << elapsedTimeF;
	ss << ", symmetric points: ";
	ss << symmetryCount;
	ss << ", closest points: ";
	ss << closestCount;
	ss << ", on center points: ";
	ss << onCenterCount;

	std::string elapsedTimeStr = ss.str();

	std::string msg = "Symmetry map built in: " + elapsedTimeStr;
	log.Message(LXe_INFO, msg.c_str());
	return true;
}

/*
 Takes an index to the symmetry map and returns 2 symmetric points under this index
 */

bool
PointSymmetryMap::getSymmetricPointIndex(unsigned int index, unsigned int *symmetricIndex)
{
    bool result = false;
    if ( index < _symmap.size() )
    {
        *symmetricIndex = _symmap.at(index);
        result = (*symmetricIndex != emptyMapElement);
    }
    return result;
}

bool
PointSymmetryMap::_findClosestSymmetricPoint(CLxUser_Point &point, CLxUser_Polygon &polygon, LXtPointID &symmetricPointID)
{
    CLxFVector posLocal;
    
    LXtVector hitPos, hitNorm;
    double hitDist;
    
    point.Pos(posLocal);
	LXtPointID pointID = point.ID();
    posLocal.v[0] *= -1.0;
    
    CLxVector dPosLocal(posLocal);
    
    if (LXx_OK(polygon.Closest(0.0, dPosLocal, hitPos, hitNorm, &hitDist)))
    {
        double shortestDistance = 1000000.0;
        
        CLxUser_Point pointSymmetric;
        point.Spawn(pointSymmetric);
        
        unsigned int vertexCount;
        polygon.VertexCount(&vertexCount);
        for (unsigned int v = 0; v < vertexCount; v++)
        {
            LXtPointID pID;
            unsigned int pIndex;
            
            polygon.VertexByIndex(v, &pID);
            pointSymmetric.Select(pID);
            pointSymmetric.Index(&pIndex);
            
            CLxFVector closestVertPos;
            pointSymmetric.Pos(closestVertPos);
            
            CLxVector distanceVector(posLocal);
            
            distanceVector -= closestVertPos;
            double distance = distanceVector.length();
            
            if (distance < shortestDistance)
            {
                shortestDistance = distance;
                symmetricPointID = pID;
            }
        }

		// Closest point is the same as the queried point.
		// In such case we consider that queried point has no symmetry.
		// I should probably mark it as point on center.
		if (symmetricPointID == pointID)
		{
			return false;
		}
    }
    else
    {
        return false;
    }
    
    return true;
}

