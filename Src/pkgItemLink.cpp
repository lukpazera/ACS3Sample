
#include <map>

#include <lxu_package.hpp>
#include <lxidef.h>
#include <lxu_vector.hpp>
#include <lxu_matrix.hpp>

#define ITEM_LINK_GRAPH "rs.itemLink"

namespace {
    const char* ITEM_LINK_PKG_NAME = "rs.pkg.itemLink";
};

namespace rs {
    namespace itemLinkPackage {
        
        static const char* CHAN_ENABLE = "rsilEnable";
        static const char* CHAN_PATTERN = "rsilPattern";
        static const char* CHAN_THICKNESS = "rsilThickness";
        static const char* CHAN_OPACITY = "rsilOpacity";
        static const char* CHAN_POINT_SIZE = "rsilPointSize";
        static const char* CHAN_COLOR_TYPE = "rsilColorType";
        static const char* CHAN_COLOR = "rsilColor";
        static const char* CHAN_COLOR_R = "rsilColor.R";
        static const char* CHAN_COLOR_G = "rsilColor.G";
        static const char* CHAN_COLOR_B = "rsilColor.B";
		static const char* CHAN_OFFSET_FROM = "rsilFromOffset";
		static const char* CHAN_OFFSET_TO = "rsilToOffset";
        
        static LXtTextValueHint patternHint[] = {
            0, "none",
            1, "dots",
            2, "dotslong",
            3, "dash",
            4, "dashlong",
            5, "dashxlong",
            6, "dotdash",
            -1, NULL
        };

        static LXtTextValueHint colorHint[] = {
            0, "wire",
            1, "fill",
            2, "custom",
            -1, NULL
        };

        static std::map<int,int> createPatternLineMap()
        {
            std::map<int,int> m;
            m[0] = 0;
            m[1] = LXiLPAT_DOTS;
            m[2] = LXiLPAT_DOTSLONG;
            m[3] = LXiLPAT_DASH;
            m[4] = LXiLPAT_DASHLONG;
            m[5] = LXiLPAT_DASHXLONG;
            m[6] = LXiLPAT_DOTDASH;

            return m;
        }
        
        static std::map<int, int> linePatternMap = createPatternLineMap();
        
        class CPackage : public CLxPackage
        {
        public:
            
        };
        
        class CChannels : public CLxChannels
        {
        public:
            
            void init_chan(CLxAttributeDesc &desc)
            {
                desc.add(CHAN_ENABLE, LXsTYPE_BOOLEAN);
                desc.default_val(1);

                desc.add(CHAN_PATTERN, LXsTYPE_INTEGER);
                desc.set_hint(patternHint);
                desc.default_val(0);

                desc.add(CHAN_THICKNESS, LXsTYPE_INTEGER);
                desc.default_val(2);
           
                desc.add(CHAN_OPACITY, LXsTYPE_PERCENT);
                desc.default_val(1.0);

                desc.add(CHAN_POINT_SIZE, LXsTYPE_INTEGER);
                desc.default_val(4);
                desc.set_min(0);
                
                desc.add(CHAN_COLOR_TYPE, LXsTYPE_INTEGER);
                desc.set_hint(colorHint);
                desc.default_val(0);
                
                desc.add(CHAN_COLOR, LXsTYPE_COLOR1);
                desc.vector_type(LXsVECTYPE_RGB);
                LXtVector color;
                LXx_VSET(color, 0.6);
                desc.default_val(color);

				desc.add(CHAN_OFFSET_FROM, LXsTYPE_BOOLEAN);
				desc.default_val(0);

				desc.add(CHAN_OFFSET_TO, LXsTYPE_BOOLEAN);
				desc.default_val(0);
            }
        };
        
        static CLxMeta_Channels<CChannels> channels_meta;
        static CLxMeta_Package<CPackage> package_meta (ITEM_LINK_PKG_NAME);

        class CViewItem3D :
        public CLxViewItem3D
        {
        public:
            /*
             * draw() is called to allow the item to draw itself in 3D.
             *
             * We read the channels for this item into a local CChannel (which would
             * be needed if the channels affected the drawing).
             */
            void
            draw (
                  CLxUser_Item &item,
                  CLxUser_ChannelRead &chan,
                  CLxUser_StrokeDraw &stroke,
                  int selFlags,
                  const CLxVector &wireColor) LXx_OVERRIDE
            {
                CChannels channels;
                channels_meta->chan_read (chan, item, &channels);
   
                int enable = chan.IValue(item, CHAN_ENABLE);
                if (enable == 0) {
                    return;
                }

                int lineThickness = chan.IValue(item, CHAN_THICKNESS);
                int linePatternHint = chan.IValue(item, CHAN_PATTERN);
                int linePattern = linePatternMap.at(linePatternHint);
                double opacity = chan.FValue(item, CHAN_OPACITY);
                double pointSize = (double)chan.IValue(item,CHAN_POINT_SIZE);
				int addOffsetFrom = chan.IValue(item, CHAN_OFFSET_FROM);
				int addOffsetTo = chan.IValue(item, CHAN_OFFSET_TO);

                // Drawing happens only when there's a target item
                // on the item link graph.
                CLxUser_ItemGraph itemLinkGraph;
                CLxUser_Scene scene;
                CLxUser_Item targetItem;
                item.Context(scene);
                scene.GraphLookup(ITEM_LINK_GRAPH, itemLinkGraph);
                unsigned links = itemLinkGraph.Forward(item);
                if (0 < links)
                {
                    itemLinkGraph.Forward(item, 0, targetItem);
                }
                else
                {
                    return;
                }
                
                CLxUser_Matrix itemXfrm;
                CLxUser_Matrix targetXfrm;
                LXtVector targetWPos;
                LXtVector vec;
                
                chan.Object(item, "worldMatrix", itemXfrm);
                chan.Object(targetItem, "worldMatrix", targetXfrm);

                targetXfrm.GetOffset(targetWPos);
				CLxMatrix4 targetXfrmM4(targetXfrm);
				CLxMatrix4 targetWRotXfrm = targetXfrmM4.asRotateMatrix();

                // Invert mesh world transform matrix.
                CLxUser_Value itemXfrmVal;
                CLxUser_Matrix invertedItemXfrm;
                _invertMatrix(itemXfrm, itemXfrmVal, invertedItemXfrm);

				// Add offsets if needed
				CLxVector offsetFrom;
				if (item.PackageTest("glItemShape") == LXe_TRUE)
				{
					if (addOffsetFrom == 1)
					{
						offsetFrom.v[0] = chan.FValue(item, "isOffset.X");
						offsetFrom.v[1] = chan.FValue(item, "isOffset.Y");
						offsetFrom.v[2] = chan.FValue(item, "isOffset.Z");
					}
				}

				if (targetItem.PackageTest("glItemShape") == LXe_TRUE)
				{
					if (addOffsetTo == 1)
					{
						CLxVector offsetTo;
						offsetTo.v[0] = chan.FValue(targetItem, "isOffset.X");
						offsetTo.v[1] = chan.FValue(targetItem, "isOffset.Y");
						offsetTo.v[2] = chan.FValue(targetItem, "isOffset.Z");

						// We need to multiply this offset by target item's world matrix.
						// Then we can add it to the target WPos.
						offsetTo *= targetWRotXfrm;
						LXx_VADD(targetWPos, offsetTo.v);
					}
				}

                // This gets the position vector for target in drawn item's space.
                invertedItemXfrm.MultiplyVector(targetWPos, vec);

                CLxVector color(0.6, 0.6, 0.6);
        
    			// If "selected" flag is on we draw with the color that was
                // passed by MODO, this will be selection color.
                // We parse color settings otherwise.
                if (selFlags & LXiSELECTION_SELECTED)
                {
                    color = wireColor;
                }
                else
                {
                    int colorType = chan.IValue(item, CHAN_COLOR_TYPE);
                    switch (colorType) {
                        case 0: // wire
                        {
                            color = wireColor;
                            break;
                        }
                        case 1: // fill
                        {
                            if (LXe_TRUE == item.PackageTest("glDraw"))
                            {
                                color.v[0] = chan.FValue(item, "fillColor.R");
                                color.v[1] = chan.FValue(item, "fillColor.G");
                                color.v[2] = chan.FValue(item, "fillColor.B");
                            }
                            else
                            {
                                color = wireColor;
                            }
                            break;
                        }
                        case 2: // custom
                        {
                            color.v[0] = chan.FValue(item, CHAN_COLOR_R);
                            color.v[1] = chan.FValue(item, CHAN_COLOR_G);
                            color.v[2] = chan.FValue(item, CHAN_COLOR_B);
                            break;
                        }
                        default:
                            break;
                    }
                    
                    // Need to make sure colours are a tab bit brighter on rollover.
                    // But only when we do not deal with wireframe color, this one
                    // will be adjusted by MODO already.
                    if ((selFlags & LXiSELECTION_ROLLOVER) && colorType != 0) // 0 means wireframe
                    {
                        CLxVector rollOverOffset(0.2, 0.2, 0.2);
                        color += rollOverOffset;
                    }
                }
                
                if (pointSize > 0)
                {
                    // Draw two points at beginning and end of the line.
                    stroke.BeginPoints(pointSize, color, opacity);
                    stroke.Vertex (offsetFrom.v, LXiSTROKE_ABSOLUTE);
                    stroke.Vertex (vec, LXiSTROKE_ABSOLUTE);
                }
                
                // Draw the line
                stroke.BeginWD (LXiSTROKE_LINES, color, opacity, lineThickness, linePattern);
                stroke.Vertex (offsetFrom.v, LXiSTROKE_ABSOLUTE);
                stroke.Vertex (vec, LXiSTROKE_ABSOLUTE);
            }
        
        private:
            void _invertMatrix(CLxUser_Matrix mat, CLxUser_Value &val, CLxUser_Matrix &invMat)
            {
                CLxUser_ValueService _valService;
                // Invert mesh world transform matrix.
                LXtMatrix4 mat4;
                mat.Get4(mat4);
                _valService.NewValue(val, LXsTYPE_MATRIX4);
                
                invMat.set(val);
                invMat.Set4 (mat4);
                invMat.Invert();
            }
            
            CLxUser_ValueService _valService;
        };
        
        static CLxMeta_ViewItem3D<CViewItem3D>		v3d_meta;
        
        static CLxMetaRoot root_meta;
        
        void initialize ()
        {
            package_meta.add (&v3d_meta);
            package_meta.add_tag(LXsPKG_GRAPHS, ITEM_LINK_GRAPH);
            
            root_meta.add (&channels_meta);
            root_meta.add (&package_meta);
            
            root_meta.initialize();
        }
    }
    
} // end rs namespace
