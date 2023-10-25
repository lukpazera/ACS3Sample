//
//  meshPartitioner.cpp
//  AutoCharacterSetup
//
//  Created by Lukasz Pazera on 16/06/17.
//  Copyright © 2017 Forest In Rain. All rights reserved.
//

#include <map>
#include <sstream>

#include <lx_action.hpp>
#include <lx_mesh.hpp>
#include <lxidef.h>
#include <lxpackage.h>
#include <lxu_select.hpp>

#include "meshPartitioner.hpp"
#include "util.hpp"


void
MeshPartitioner::SetSubdivide(bool subdivide)
{
    _subdivide = subdivide;
}

void
MeshPartitioner::SetDoubleSided(bool doubleSided)
{
    _doubleSided = doubleSided;
}

std::vector<CLxUser_Item>
MeshPartitioner::ByWeights(std::vector<std::string> weightMapNames)
{
	PartitionMap partitionMap;
    std::vector<CLxUser_Item> cutMeshes;

    GeneratePartitionMap(weightMapNames, partitionMap);
    CutMeshByPartitionMap(partitionMap, cutMeshes);
    return cutMeshes;
}

void
MeshPartitioner::PartitionIntoSelectionSets(std::vector<std::string> weightMapNames)
{
	PartitionMap partitionMap;

	GeneratePartitionMap(weightMapNames, partitionMap);
	CreateSelectionSetsByPartitionMap(partitionMap);
}

bool
MeshPartitioner::GeneratePartitionMap(std::vector<std::string> &weightMapNames, PartitionMap &partitionMap)
{
    typename std::vector<std::string>::iterator wmapIt = weightMapNames.begin();
    for (; wmapIt != weightMapNames.end(); ++wmapIt)
    {
		// Make sure the weight map to process is really there on the mesh.
		if (_meshMap.SelectByName(LXi_VMAP_WEIGHT, wmapIt->c_str()) == LXe_FALSE)
		{
			continue;
		}

        std::vector<LXtPolygonID> polygonsList;
        partitionMap[*wmapIt] = polygonsList;
    }
    
    unsigned int polyCount;
    _mesh.PolygonCount(&polyCount);

    std::vector<float> weightMapFactors;
    if (_normalize)
    {
    	for (unsigned int w = 0; w < weightMapNames.size(); w++)
    	{
            float factor = CalculateWeightMapNormalizationFactor(weightMapNames[w]);
            printf("Weight FACTOR: %f \n", factor);
            weightMapFactors.push_back(factor);
    	}
    }

    for (unsigned int i = 0; i < polyCount; i++)
    {
        _polygon.SelectByIndex(i);

        std::string strongestWeightMap;
        float strongestWeight = 0.0;

        //wmapIt = weightMapNames.begin();
        for (unsigned int w = 0; w < weightMapNames.size(); w++)
        {
			if (_meshMap.SelectByName(LXi_VMAP_WEIGHT, weightMapNames[w].c_str()) == LXe_FALSE)
			{
				continue;
			}

            LXtMeshMapID mapID = _meshMap.ID();
            
            float polygonWeightAmount = 0.0;
            unsigned int polyVertexCount;
            _polygon.VertexCount(&polyVertexCount);
            for (unsigned int vx = 0; vx < polyVertexCount; vx++)
            {
                // get weights here.
                LXtPointID vertID;
                float value;
                _polygon.VertexByIndex(vx, &vertID);
                _polygon.MapEvaluate(mapID, vertID, &value);
                
                if (_normalize)
                {
                    value *= weightMapFactors[w];
                }

                polygonWeightAmount += value;
            }

            polygonWeightAmount /= (float) polyVertexCount;

            if (polygonWeightAmount > strongestWeight)
            {
                strongestWeight = polygonWeightAmount;
                strongestWeightMap = weightMapNames[w];
            }
        }

        partitionMap[strongestWeightMap].push_back(_polygon.ID());

        printf("%d  %s\n", i, strongestWeightMap.c_str());
    }

    /*
     DEBUG output.
    typename std::map<std::string, std::vector<LXtPolygonID>>::iterator mapIt = partitionMap.begin();
    for (; mapIt != partitionMap.end(); ++mapIt)
    {
        printf("%s : ", mapIt->first.c_str());
        typename std::vector<LXtPolygonID>::iterator polyIt = mapIt->second.begin();
        for (; polyIt != mapIt->second.end(); ++polyIt)
        {
            printf("%d, ", *polyIt);
        }
        printf("\n");
    }
	*/
    return true;
}

float MeshPartitioner::CalculateWeightMapNormalizationFactor(std::string &weightMapName)
{
    float factor = 1.0;
    float maxValue = 0.0;

	if (_meshMap.SelectByName(LXi_VMAP_WEIGHT, weightMapName.c_str()) == LXe_FALSE)
	{
		return factor;
	}

    LXtMeshMapID mapID =_meshMap.ID();
    
    unsigned int pointCount;
    _mesh.PointCount(&pointCount);
    
    for (unsigned int i = 0; i < pointCount; i++)
    {
        float value = 0.0;
        _point.SelectByIndex(i);
        _point.MapEvaluate(mapID, &value);
        if (value > maxValue)
        {
            maxValue = value;
        }
    }

    printf("Max value for map: %s : %f \n", weightMapName.c_str(), maxValue);

    if (0.0 < maxValue && maxValue < 1.0)
    {
        factor = 1.0 / maxValue;
    }
    return factor;
}

/*
 * Create new mesh items from partition map and add them to the cut meshes list.
 */
bool MeshPartitioner::CutMeshByPartitionMap(PartitionMap &partitionMap, std::vector<CLxUser_Item> &cutMeshes)
{
    CLxUser_CommandService commandService;
    CLxItemSelection itemSelection;
    std::string meshBaseName;
    _meshItem.GetUniqueName(meshBaseName);
    
    typename PartitionMap::iterator mapIt = partitionMap.begin();
    for (; mapIt != partitionMap.end(); ++mapIt)
    {
        itemSelection.Clear();
        itemSelection.Select(_meshItem);
    
    	util::ClearAllPolygons();

        // Skip weight maps that have no polygons associated.
        if (mapIt->second.empty())
        {
            continue;
        }

        CLxUser_SelectionService selectionService;
        selectionService.StartBatch();

        typename std::vector<LXtPolygonID>::iterator polyIt = mapIt->second.begin();
        for (; polyIt != mapIt->second.end(); ++polyIt)
        {
            util::SelectPolygon(*polyIt, _mesh);
            //printf("%d, ", *polyIt);
        }

        selectionService.EndBatch();

      	commandService.ExecuteArgString(-1, LXiCTAG_NULL, "select.type polygon" );
      	commandService.ExecuteArgString(-1, LXiCTAG_NULL, "select.copy" );

        CLxUser_Item newProxyItem;
        if (!_scene.ItemAdd(LXi_CIT_MESH, newProxyItem))
        {
            continue;
        }

        std::string proxyItemName = meshBaseName + "-" + mapIt->first;
        proxyItemName += "-Proxy";
        newProxyItem.SetName(proxyItemName.c_str());
        cutMeshes.push_back(newProxyItem);

        itemSelection.Clear();
        itemSelection.Select(newProxyItem);

        commandService.ExecuteArgString(-1, LXiCTAG_NULL, "select.type polygon" );
        commandService.ExecuteArgString(-1, LXiCTAG_NULL, "select.paste" );

        if (_subdivide)
        {
        	commandService.ExecuteArgString(-1, LXiCTAG_NULL, "poly.subdivide ccsds" );
      		commandService.ExecuteArgString(-1, LXiCTAG_NULL, "select.copy" );
        }
        
        if (_doubleSided)
        {
        	commandService.ExecuteArgString(-1, LXiCTAG_NULL, "poly.flip" );
            commandService.ExecuteArgString(-1, LXiCTAG_NULL, "poly.setMaterial {Bind Proxy Inner Side} {0.0 0.0 0.0} 0.0 0.0 true false" );
            _tweakInnerMaterial(); // This should really be called only once, the first time material is created.
        	commandService.ExecuteArgString(-1, LXiCTAG_NULL, "select.paste" );
        }
        
        util::ClearAllPolygons();
    }

    return true;
}

/*
 * Creates selection sets from partition map.
 */
bool MeshPartitioner::CreateSelectionSetsByPartitionMap(PartitionMap &partitionMap)
{
	CLxUser_CommandService commandService;
	CLxItemSelection itemSelection;
	std::string meshBaseName;
	_meshItem.GetUniqueName(meshBaseName);

	// Be sure to set component mode to polygon
	// so the created sets will be polygon sets
	commandService.ExecuteArgString(-1, LXiCTAG_NULL, "select.type polygon");

	typename PartitionMap::iterator mapIt = partitionMap.begin();
	for (; mapIt != partitionMap.end(); ++mapIt)
	{
		itemSelection.Clear();
		itemSelection.Select(_meshItem);

		util::ClearAllPolygons();

		// Skip weight maps that have no polygons associated.
		if (mapIt->second.empty())
		{
			continue;
		}

		CLxUser_SelectionService selectionService;
		selectionService.StartBatch();

		typename std::vector<LXtPolygonID>::iterator polyIt = mapIt->second.begin();
		for (; polyIt != mapIt->second.end(); ++polyIt)
		{
			util::SelectPolygon(*polyIt, _mesh);
		}

		selectionService.EndBatch();

		std::string selectionSetName = meshBaseName + "-" + mapIt->first;
		std::string commandString = "select.editSet {" + selectionSetName + "} set";
		commandService.ExecuteArgString(-1, LXiCTAG_NULL, commandString.c_str());
	}

	util::ClearAllPolygons();
	return true;
}

/*
 * This is crappy function that tweaks the freshly created material to have
 * Fresnel amount set to 0.
 * It looks for an advanced material item in item selection and then
 * sets the fresnel to 0 for this material.
 */
void MeshPartitioner::_tweakInnerMaterial()
{
    modo::selection::Item itemSelection;
    modo::selection::Item::ItemList selectedItems;
    CLxUser_Item materialItem;
    LXtItemType materialType;
    _sceneService.ItemTypeLookup("advancedMaterial", &materialType);
    
    itemSelection.GetList(selectedItems);
    for(auto it = selectedItems.begin(); it != selectedItems.end(); it++)
    {
        if (it->Type() == materialType) {
            std::ostringstream stringStream;
            stringStream << "item.channel advancedMaterial$specFres 0.0 item:{";
            stringStream << it->GetIdentity();
            stringStream << "}";
            _commandService.ExecuteArgString(-1, LXiCTAG_NULL, stringStream.str().c_str());
        }
    }
    
}
