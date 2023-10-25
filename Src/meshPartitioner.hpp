//
//  meshPartitioner.hpp
//  AutoCharacterSetup
//
//  Created by Lukasz Pazera on 16/06/17.
//  Copyright © 2017 Forest In Rain. All rights reserved.
//

#ifndef meshPartitioner_hpp
#define meshPartitioner_hpp

#include <vector>
#include <map>

#include <lx_item.hpp>
#include <lx_command.hpp>

#include "modo.hpp"


class MeshPartitioner {

public:
    MeshPartitioner(CLxUser_Item &meshItem):
    _meshItem(meshItem),
    _normalize(false),
    _doubleSided(true),
    _subdivide(false)
    {
        // This needs to throw an exception if constructor fails.
        _meshItem.GetContext(_scene);
        _meshItem.GetReadOnlyMesh(_mesh);
        _mesh.PolygonAccessor(_polygon);
        _mesh.PointAccessor(_point);
        _mesh.MeshMapAccessor(_meshMap);
    }

    ~MeshPartitioner() {}
    
    void SetNormalize(bool normalize);
    void SetDoubleSided(bool doubleSided);
    void SetSubdivide(bool subdivide);
    std::vector<CLxUser_Item> ByWeights(std::vector<std::string> weightMapNames);
    std::vector<CLxUser_Item> ByJoints(std::vector<CLxUser_Item> jointList);
	void PartitionIntoSelectionSets(std::vector<std::string> weightMapNames);
    

private:
    typedef std::map<std::string, std::vector<LXtPolygonID>> PartitionMap;
    
    bool GeneratePartitionMap(std::vector<std::string> &weightMapNames, PartitionMap &partitionMap);
    bool CutMeshByPartitionMap(PartitionMap &partitionMap, std::vector<CLxUser_Item> &cutMeshes);
	bool CreateSelectionSetsByPartitionMap(PartitionMap &partitionMap);
    float CalculateWeightMapNormalizationFactor(std::string &weightMapName);
    void _tweakInnerMaterial();
    
    bool _normalize;
    bool _doubleSided;
    bool _subdivide;

    CLxUser_Scene _scene;
    modo::item::Mesh _meshItem;
    CLxUser_Mesh _mesh;
    CLxUser_Polygon _polygon;
    CLxUser_Point _point;
    CLxUser_MeshMap _meshMap;
    
    CLxUser_SceneService _sceneService;
    CLxUser_CommandService _commandService;
};


#endif /* meshPartitioner_hpp */
